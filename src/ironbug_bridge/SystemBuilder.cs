using System.Collections;
using System.Globalization;
using System.Reflection;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace IronbugBridge;

/// <summary>
/// Instantiates real Ironbug.HVAC objects from a compact JSON system draft,
/// builds IB_HVACSystem, serializes via official ToJson(), and validates in-memory
/// via IB_HVACSystem.SaveHVAC(OpenStudio.Model).
/// </summary>
internal sealed class SystemBuilder
{
    private readonly BridgeRuntime _runtime;

    public SystemBuilder(BridgeRuntime runtime)
    {
        _runtime = runtime;
    }

    public Dictionary<string, object?> Build(JsonElement draft)
    {
        if (draft.ValueKind != JsonValueKind.Object)
            throw new ArgumentException("Build draft must be a JSON object.");

        var componentSpecs = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        if (draft.TryGetProperty("components", out var compsEl) && compsEl.ValueKind == JsonValueKind.Object)
        {
            foreach (var prop in compsEl.EnumerateObject())
            {
                componentSpecs[prop.Name] = prop.Value;
            }
        }

        var instances = new Dictionary<string, object>(StringComparer.Ordinal);
        var visiting = new HashSet<string>(StringComparer.Ordinal);

        object ResolveComponent(string id)
        {
            if (instances.TryGetValue(id, out var existing))
                return existing;
            if (!componentSpecs.TryGetValue(id, out var spec))
                throw new KeyNotFoundException($"Referenced component id '{id}' is not defined in components.");
            if (!visiting.Add(id))
                throw new InvalidOperationException($"Cyclic dependency detected while building component '{id}'.");

            try
            {
                var created = InstantiateComponent(id, spec, ResolveComponent, componentSpecs);
                instances[id] = created;
                return created;
            }
            finally
            {
                visiting.Remove(id);
            }
        }

        // Instantiate all declared components first so shared instances keep identical TrackingIDs
        foreach (var compId in componentSpecs.Keys)
        {
            ResolveComponent(compId);
        }

        // Build or resolve IB_ThermalZone instances keyed by room_name (two-pass so plenums can reference any zone)
        var zonesByRoom = new Dictionary<string, object>(StringComparer.Ordinal);
        var zoneElsByRoom = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        if (draft.TryGetProperty("thermal_zones", out var tzListEl) && tzListEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var tzEl in tzListEl.EnumerateArray())
            {
                var roomName = GetRequiredString(tzEl, "room_name");
                if (zonesByRoom.ContainsKey(roomName))
                    throw new ArgumentException($"Duplicate thermal_zones entry for room_name '{roomName}'.");

                var zone = CreateThermalZone(roomName, tzEl, ResolveComponent, componentSpecs);
                zonesByRoom[roomName] = zone;
                zoneElsByRoom[roomName] = tzEl;
            }
            foreach (var kv in zoneElsByRoom)
            {
                ApplyThermalZonePlenums(kv.Key, zonesByRoom[kv.Key], kv.Value, zonesByRoom, ResolveComponent);
            }
        }

        // Air loops
        var airLoopBaseType = _runtime.ResolveHvacType("IB_AirLoopHVAC");
        var airLoops = (IList)Activator.CreateInstance(typeof(List<>).MakeGenericType(airLoopBaseType))!;
        var assignedZoneRooms = new HashSet<string>(StringComparer.Ordinal);

        if (draft.TryGetProperty("air_loops", out var alListEl) && alListEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var alEl in alListEl.EnumerateArray())
            {
                var airLoop = BuildAirLoop(alEl, ResolveComponent, componentSpecs, zonesByRoom, assignedZoneRooms);
                airLoops.Add(airLoop);
            }
        }

        // Put any remaining thermal zones not assigned to an air loop into IB_NoAirLoop
        var unassignedZones = zonesByRoom
            .Where(kv => !assignedZoneRooms.Contains(kv.Key))
            .Select(kv => kv.Value)
            .ToList();
        if (unassignedZones.Count > 0)
        {
            var noAirLoopType = _runtime.ResolveHvacType("IB_NoAirLoop");
            var noAirLoop = Activator.CreateInstance(noAirLoopType)!;
            var addTz = noAirLoopType.GetMethod("AddThermalZones")!;
            foreach (var z in unassignedZones)
            {
                addTz.Invoke(noAirLoop, new[] { z });
            }
            airLoops.Add(noAirLoop);
        }

        // Plant loops
        var plantLoopType = _runtime.ResolveHvacType("IB_PlantLoop");
        var plantLoops = (IList)Activator.CreateInstance(typeof(List<>).MakeGenericType(plantLoopType))!;
        if (draft.TryGetProperty("plant_loops", out var plListEl) && plListEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var plEl in plListEl.EnumerateArray())
            {
                var plantLoop = BuildPlantLoop(plEl, ResolveComponent, componentSpecs);
                plantLoops.Add(plantLoop);
            }
        }

        // VRF systems
        var vrfBaseType = ResolveVrfListElementType();
        var vrfs = (IList)Activator.CreateInstance(typeof(List<>).MakeGenericType(vrfBaseType))!;
        if (draft.TryGetProperty("vrf_systems", out var vrfListEl) && vrfListEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var vrfEl in vrfListEl.EnumerateArray())
            {
                var vrf = BuildVrfSystem(vrfEl, ResolveComponent);
                vrfs.Add(vrf);
            }
        }

        // Construct IB_HVACSystem
        var sysType = _runtime.ResolveHvacType("IB_HVACSystem");
        var sysCtor = sysType.GetConstructors()[0];
        var sys = sysCtor.Invoke(new object[] { airLoops, plantLoops, vrfs });

        if (draft.TryGetProperty("display_name", out var dnEl) && dnEl.ValueKind == JsonValueKind.String)
        {
            var dnProp = sysType.GetProperty("DisplayName");
            if (dnProp != null && dnProp.CanWrite)
            {
                dnProp.SetValue(sys, dnEl.GetString());
            }
        }
        if (draft.TryGetProperty("energy_management_system", out var emsEl) && emsEl.ValueKind == JsonValueKind.String)
        {
            var emsVal = emsEl.GetString();
            if (!string.IsNullOrWhiteSpace(emsVal))
            {
                var emsProp = sysType.GetProperty("EnergyManagementSystem");
                if (emsProp != null && emsProp.CanWrite)
                {
                    emsProp.SetValue(sys, ResolveComponent(StripRefPrefix(emsVal)));
                }
            }
        }
        if (draft.TryGetProperty("electric_load_center", out var elcEl) && elcEl.ValueKind == JsonValueKind.String)
        {
            var elcVal = elcEl.GetString();
            if (!string.IsNullOrWhiteSpace(elcVal))
            {
                var elcProp = sysType.GetProperty("ElectricLoadCenter");
                if (elcProp != null && elcProp.CanWrite)
                {
                    elcProp.SetValue(sys, ResolveComponent(StripRefPrefix(elcVal)));
                }
            }
        }

        var toJsonMethod = sysType.GetMethod("ToJson", new[] { typeof(bool) })
            ?? throw new MissingMethodException("IB_HVACSystem.ToJson(bool) not found.");
        var specJson = (string)toJsonMethod.Invoke(sys, new object[] { false })!;

        // Round-trip check via official FromJson
        var fromJsonMethod = sysType.GetMethod("FromJson", BindingFlags.Public | BindingFlags.Static)
            ?? throw new MissingMethodException("IB_HVACSystem.FromJson(string) not found.");
        var roundtripped = fromJsonMethod.Invoke(null, new object[] { specJson })
            ?? throw new InvalidOperationException("IB_HVACSystem.FromJson returned null after ToJson().");

        var summary = SummarizeSystem(sysType, roundtripped);
        return new Dictionary<string, object?>
        {
            ["specification_json"] = specJson,
            ["summary"] = summary,
        };
    }

    public Dictionary<string, object?> Inspect(string specificationJson)
    {
        var sysType = _runtime.ResolveHvacType("IB_HVACSystem");
        var fromJsonMethod = sysType.GetMethod("FromJson", BindingFlags.Public | BindingFlags.Static)!;
        var sys = fromJsonMethod.Invoke(null, new object[] { specificationJson })
            ?? throw new InvalidOperationException("IB_HVACSystem.FromJson returned null.");
        return SummarizeSystem(sysType, sys);
    }

    public Dictionary<string, object?> Validate(
        string specificationJson,
        IReadOnlyList<string> roomNames,
        string? osmPath = null,
        bool? runForwardTranslator = null)
    {
        var sysType = _runtime.ResolveHvacType("IB_HVACSystem");
        var fromJsonMethod = sysType.GetMethod("FromJson", BindingFlags.Public | BindingFlags.Static)!;
        var sys = fromJsonMethod.Invoke(null, new object[] { specificationJson })
            ?? throw new InvalidOperationException("IB_HVACSystem.FromJson returned null.");

        var summary = SummarizeSystem(sysType, sys);
        var zoneNames = new SortedSet<string>(StringComparer.Ordinal);
        if (summary["thermal_zones"] is IEnumerable<string> existingZones)
        {
            foreach (var z in existingZones) zoneNames.Add(z);
        }
        foreach (var r in roomNames)
        {
            if (!string.IsNullOrWhiteSpace(r)) zoneNames.Add(r.Trim());
        }

        var osAsm = _runtime.OpenStudioAssembly;
        var osModelType = osAsm.GetType("OpenStudio.Model")
            ?? throw new TypeLoadException("OpenStudio.Model type not found.");
        var osZoneType = osAsm.GetType("OpenStudio.ThermalZone")
            ?? throw new TypeLoadException("OpenStudio.ThermalZone type not found.");

        var osRuntimeVersion = GetOpenStudioRuntimeVersion(osAsm);
        var ironbugHvacVersion = _runtime.HvacAssembly.GetName().Version?.ToString();
        var ironbugOsRefVersion = _runtime.HvacAssembly.GetReferencedAssemblies()
            .FirstOrDefault(a => string.Equals(a.Name, "OpenStudio", StringComparison.OrdinalIgnoreCase))
            ?.Version?.ToString();

        var errors = new List<string>();
        var warnings = new List<string>();
        var vtWarnings = new List<string>();
        var vtErrors = new List<string>();
        string? osmVersion = null;
        object? osModel = null;
        bool hasExternalOsm = !string.IsNullOrWhiteSpace(osmPath);

        try
        {
            if (hasExternalOsm)
            {
                var fullOsmPath = Path.GetFullPath(osmPath!);
                if (!File.Exists(fullOsmPath))
                {
                    errors.Add($"OSM file not found at '{fullOsmPath}'.");
                    osModel = Activator.CreateInstance(osModelType)!;
                }
                else
                {
                    osmVersion = ExtractOsmVersionFromFile(fullOsmPath);
                    osModel = LoadOsmModelWithDiagnostics(
                        osAsm,
                        osModelType,
                        fullOsmPath,
                        ref osmVersion,
                        errors,
                        warnings,
                        vtWarnings,
                        vtErrors);
                }
            }
            else
            {
                osModel = Activator.CreateInstance(osModelType)!;
                var setNameMethod = osZoneType.GetMethod("setName", new[] { typeof(string) });
                foreach (var zName in zoneNames)
                {
                    var osZone = Activator.CreateInstance(osZoneType, new[] { osModel })!;
                    setNameMethod?.Invoke(osZone, new object[] { zName });
                }
            }

            bool saveOk = false;
            if (errors.Count == 0)
            {
                var savedErr = Console.Error;
                var logCapture = new StringWriter();
                var utilType = _runtime.HvacAssembly.GetTypes().FirstOrDefault(t => t.Name == "IB_Utility");
                var startSaving = utilType?.GetMethod("StartSaving", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
                var endSaving = utilType?.GetMethod("EndSaving", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
                bool savingStarted = false;
                try
                {
                    Console.SetError(logCapture);
                    if (startSaving != null)
                    {
                        startSaving.Invoke(null, null);
                        savingStarted = true;
                    }
                    var saveMethod = sysType.GetMethod("SaveHVAC", new[] { osModelType })
                        ?? throw new MissingMethodException("IB_HVACSystem.SaveHVAC(OpenStudio.Model) not found.");
                    var result = saveMethod.Invoke(sys, new[] { osModel });
                    saveOk = result is bool b && b;
                    if (!saveOk)
                    {
                        errors.Add("IB_HVACSystem.SaveHVAC(OpenStudio.Model) returned false.");
                    }
                    else
                    {
                        ApplyZoneEquipmentPriorities(sysType, sys, osAsm, osModelType, osModel, warnings);
                    }
                }
                catch (Exception ex)
                {
                    var inner = ex is TargetInvocationException tie && tie.InnerException != null ? tie.InnerException : ex;
                    errors.Add(inner.Message);
                }
                finally
                {
                    if (savingStarted && endSaving != null)
                    {
                        try { endSaving.Invoke(null, null); } catch { }
                    }
                    Console.SetError(savedErr);
                }

                var logText = logCapture.ToString();
                if (!string.IsNullOrWhiteSpace(logText))
                {
                    foreach (var line in logText.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
                    {
                        var trimmed = line.Trim();
                        if (!string.IsNullOrEmpty(trimmed)) warnings.Add(trimmed);
                    }
                }
            }

            Dictionary<string, object?>? forwardTranslatorInfo = null;
            bool shouldRunFt = runForwardTranslator ?? hasExternalOsm;
            if (shouldRunFt && saveOk && errors.Count == 0)
            {
                forwardTranslatorInfo = RunForwardTranslatorCheck(
                    osAsm,
                    osModelType,
                    osModel,
                    errors,
                    warnings,
                    vtWarnings,
                    vtErrors,
                    osmVersion,
                    osRuntimeVersion);
            }

            var osSummary = BuildOpenStudioSummary(osModelType, osModel);

            var payload = new Dictionary<string, object?>
            {
                ["valid"] = saveOk && errors.Count == 0,
                ["errors"] = errors,
                ["warnings"] = warnings,
                ["thermal_zones"] = zoneNames.ToList(),
                ["system_summary"] = summary,
                ["openstudio_summary"] = osSummary,
                ["openstudio_version"] = osRuntimeVersion,
                ["ironbug_hvac_version"] = ironbugHvacVersion,
                ["ironbug_openstudio_ref_version"] = ironbugOsRefVersion,
            };
            if (!string.IsNullOrWhiteSpace(osmVersion))
            {
                payload["osm_version"] = osmVersion;
            }
            if (vtWarnings.Count > 0 || vtErrors.Count > 0)
            {
                payload["version_translator"] = new Dictionary<string, object?>
                {
                    ["osm_version"] = osmVersion,
                    ["openstudio_version"] = osRuntimeVersion,
                    ["warnings"] = vtWarnings,
                    ["errors"] = vtErrors,
                };
            }
            if (forwardTranslatorInfo != null)
            {
                payload["forward_translator"] = forwardTranslatorInfo;
            }
            return payload;
        }
        finally
        {
            (osModel as IDisposable)?.Dispose();
        }
    }

    private Type ResolveVrfListElementType()
    {
        var sysType = _runtime.ResolveHvacType("IB_HVACSystem");
        var ctor = sysType.GetConstructors()[0];
        var vrfListType = ctor.GetParameters()[2].ParameterType;
        return vrfListType.GetGenericArguments()[0];
    }

    private object InstantiateComponent(
        string id,
        JsonElement spec,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        if (spec.ValueKind != JsonValueKind.Object)
            throw new ArgumentException($"Component '{id}' spec must be a JSON object.");

        var typeName = GetRequiredString(spec, "type");
        var type = _runtime.ResolveHvacType(typeName);
        if (type.IsAbstract || type.Name.EndsWith("_FieldSet", StringComparison.Ordinal))
            throw new ArgumentException($"Type '{type.Name}' for component '{id}' is not instantiable.");

        object instance;
        if (spec.TryGetProperty("ctor_args", out var ctorArgsEl) && ctorArgsEl.ValueKind != JsonValueKind.Null && ctorArgsEl.ValueKind != JsonValueKind.Undefined)
        {
            instance = InvokeMatchingConstructor(id, type, ctorArgsEl, resolveComponent, allSpecs);
        }
        else
        {
            var defaultCtor = type.GetConstructor(Type.EmptyTypes);
            if (defaultCtor != null)
            {
                instance = defaultCtor.Invoke(null);
            }
            else
            {
                // Check for constructor where all parameters have defaults
                var allDefaultCtor = type.GetConstructors()
                    .FirstOrDefault(c => c.GetParameters().All(p => p.HasDefaultValue));
                if (allDefaultCtor != null)
                {
                    var defaults = allDefaultCtor.GetParameters().Select(p => p.DefaultValue).ToArray();
                    instance = allDefaultCtor.Invoke(defaults);
                }
                else
                {
                    var sigs = string.Join(" | ", type.GetConstructors().Select(c =>
                        "(" + string.Join(", ", c.GetParameters().Select(p => $"{CatalogInspector.FriendlyTypeName(p.ParameterType)} {p.Name}")) + ")"));
                    throw new ArgumentException(
                        $"Component '{id}' of type '{type.Name}' requires constructor arguments in ctor_args. Available constructors: {sigs}");
                }
            }
        }

        if (spec.TryGetProperty("tracking_id", out var tidEl) && tidEl.ValueKind == JsonValueKind.String)
        {
            var tid = tidEl.GetString();
            if (!string.IsNullOrWhiteSpace(tid))
            {
                var setTracking = type.GetMethod("SetTrackingID", new[] { typeof(string) });
                setTracking?.Invoke(instance, new object[] { tid });
            }
        }

        if (spec.TryGetProperty("fields", out var fieldsEl) && fieldsEl.ValueKind == JsonValueKind.Object)
        {
            ApplyFields(id, type, instance, fieldsEl, resolveComponent, allSpecs);
        }

        if (spec.TryGetProperty("ib_properties", out var ibPropsEl) && ibPropsEl.ValueKind == JsonValueKind.Object)
        {
            ApplyIbProperties(id, type, instance, ibPropsEl, resolveComponent, allSpecs);
        }

        if (spec.TryGetProperty("children", out var childrenEl) && childrenEl.ValueKind == JsonValueKind.Array)
        {
            ApplyChildren(id, type, instance, childrenEl, resolveComponent);
        }

        if (spec.TryGetProperty("wiring", out var wiringEl) && wiringEl.ValueKind != JsonValueKind.Null && wiringEl.ValueKind != JsonValueKind.Undefined)
        {
            ApplyWiring(id, type, instance, wiringEl, resolveComponent, allSpecs);
        }

        if (spec.TryGetProperty("output_variables", out var outVarsEl) && outVarsEl.ValueKind == JsonValueKind.Array)
        {
            ApplyOutputVariables(id, type, instance, outVarsEl);
        }

        if (spec.TryGetProperty("ems_sensors", out var sensorsEl) && sensorsEl.ValueKind == JsonValueKind.Array)
        {
            ApplyEmsSensors(id, type, instance, sensorsEl, resolveComponent, allSpecs);
        }

        if (spec.TryGetProperty("ems_internal_variables", out var ivarsEl) && ivarsEl.ValueKind == JsonValueKind.Array)
        {
            ApplyEmsInternalVariables(id, type, instance, ivarsEl, resolveComponent, allSpecs);
        }

        if (spec.TryGetProperty("ems_actuators", out var actsEl) && actsEl.ValueKind == JsonValueKind.Array)
        {
            ApplyEmsActuators(id, type, instance, actsEl, resolveComponent, allSpecs);
        }

        return instance;
    }

    private object InvokeMatchingConstructor(
        string compId,
        Type type,
        JsonElement ctorArgsEl,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        var ctors = type.GetConstructors(BindingFlags.Public | BindingFlags.Instance);
        if (ctorArgsEl.ValueKind == JsonValueKind.Array)
        {
            var rawArgs = ctorArgsEl.EnumerateArray().ToList();
            foreach (var ctor in ctors.OrderBy(c => c.GetParameters().Length))
            {
                var ps = ctor.GetParameters();
                int reqCount = ps.Count(p => !p.HasDefaultValue);
                if (rawArgs.Count < reqCount || rawArgs.Count > ps.Length)
                    continue;
                try
                {
                    var converted = new object?[ps.Length];
                    for (int i = 0; i < ps.Length; i++)
                    {
                        converted[i] = i < rawArgs.Count
                            ? CoerceValue(rawArgs[i], ps[i].ParameterType, resolveComponent, allSpecs)
                            : ps[i].DefaultValue;
                    }
                    return ctor.Invoke(converted);
                }
                catch
                {
                    // Try next overload
                }
            }
            var sigs = string.Join(" | ", ctors.Select(c =>
                "(" + string.Join(", ", c.GetParameters().Select(p => $"{CatalogInspector.FriendlyTypeName(p.ParameterType)} {p.Name}")) + ")"));
            throw new ArgumentException($"No matching constructor on {type.Name} for component '{compId}' with {rawArgs.Count} ctor_args. Constructors: {sigs}");
        }

        if (ctorArgsEl.ValueKind == JsonValueKind.Object)
        {
            var dict = new Dictionary<string, JsonElement>(StringComparer.OrdinalIgnoreCase);
            foreach (var prop in ctorArgsEl.EnumerateObject())
            {
                dict[NormalizeKey(prop.Name)] = prop.Value;
            }
            foreach (var ctor in ctors.OrderByDescending(c => c.GetParameters().Length))
            {
                var ps = ctor.GetParameters();
                var pMap = ps.ToDictionary(p => NormalizeKey(p.Name ?? ""), p => p, StringComparer.OrdinalIgnoreCase);
                if (!dict.Keys.All(k => pMap.ContainsKey(k))) continue;
                if (!ps.Where(p => !p.HasDefaultValue).All(p => dict.ContainsKey(NormalizeKey(p.Name ?? "")))) continue;
                try
                {
                    var converted = new object?[ps.Length];
                    for (int i = 0; i < ps.Length; i++)
                    {
                        var key = NormalizeKey(ps[i].Name ?? "");
                        converted[i] = dict.TryGetValue(key, out var valEl)
                            ? CoerceValue(valEl, ps[i].ParameterType, resolveComponent, allSpecs)
                            : ps[i].DefaultValue;
                    }
                    return ctor.Invoke(converted);
                }
                catch
                {
                    // Try next overload
                }
            }
            var sigs = string.Join(" | ", ctors.Select(c =>
                "(" + string.Join(", ", c.GetParameters().Select(p => $"{CatalogInspector.FriendlyTypeName(p.ParameterType)} {p.Name}")) + ")"));
            throw new ArgumentException($"No matching constructor on {type.Name} for component '{compId}' with named ctor_args. Constructors: {sigs}");
        }

        throw new ArgumentException($"ctor_args for component '{compId}' must be an array or object.");
    }

    private void ApplyFields(
        string compId,
        Type type,
        object instance,
        JsonElement fieldsEl,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        var fsType = _runtime.ResolveFieldSetType(type);
        var fsInst = fsType != null ? _runtime.GetFieldSetInstance(fsType) : null;
        if (fsType == null || fsInst == null)
        {
            throw new ArgumentException($"Component '{compId}' ({type.Name}) has no FieldSet; cannot set fields.");
        }

        var fieldLookup = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);
        var validNames = new List<string>();
        if (fsInst is IEnumerable en)
        {
            foreach (var item in en)
            {
                if (item == null) continue;
                var fullName = item.GetType().GetProperty("FullName")?.GetValue(item)?.ToString();
                var nickName = item.GetType().GetProperty("NickName")?.GetValue(item)?.ToString();
                if (!string.IsNullOrWhiteSpace(fullName))
                {
                    fieldLookup.TryAdd(fullName, item);
                    fieldLookup.TryAdd(NormalizeKey(fullName), item);
                    validNames.Add(fullName);
                }
                if (!string.IsNullOrWhiteSpace(nickName))
                {
                    fieldLookup.TryAdd(nickName, item);
                    fieldLookup.TryAdd(NormalizeKey(nickName), item);
                }
            }
        }
        foreach (var prop in fsType.GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly))
        {
            if (prop.Name is "OwnerEpNote" or "Count" or "IsReadOnly") continue;
            var val = prop.GetValue(fsInst);
            if (val != null)
            {
                fieldLookup.TryAdd(prop.Name, val);
                fieldLookup.TryAdd(NormalizeKey(prop.Name), val);
            }
        }

        var customAttrsProp = type.GetProperty("CustomAttributes")
            ?? throw new MissingMemberException($"{type.Name}.CustomAttributes not found.");
        var customAttrs = customAttrsProp.GetValue(instance)!;
        var ibFieldType = _runtime.ResolveHvacType("IB_Field");
        var tryAddMethod = customAttrs.GetType().GetMethod("TryAdd", new[] { ibFieldType, typeof(object) })
            ?? throw new MissingMethodException("IB_FieldArgumentSet.TryAdd(IB_Field, object) not found.");

        foreach (var kv in fieldsEl.EnumerateObject())
        {
            if (!fieldLookup.TryGetValue(kv.Name, out var ibField) && !fieldLookup.TryGetValue(NormalizeKey(kv.Name), out ibField))
            {
                var sample = string.Join(", ", validNames.Take(12));
                throw new ArgumentException(
                    $"Unknown field '{kv.Name}' on {type.Name} (component '{compId}'). Valid fields include: {sample}");
            }

            var dataType = ibField.GetType().GetProperty("DataType")?.GetValue(ibField) as Type;
            if (kv.Value.ValueKind == JsonValueKind.String && IsNumericFieldType(dataType))
            {
                var rawText = kv.Value.GetString()?.Trim();
                if (string.Equals(rawText, "autosize", StringComparison.OrdinalIgnoreCase)
                    || string.Equals(rawText, "autocalculate", StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }
            }
            var coerced = CoerceFieldValue(compId, kv.Name, kv.Value, dataType, resolveComponent, allSpecs);
            try
            {
                tryAddMethod.Invoke(customAttrs, new[] { ibField, coerced });
            }
            catch (Exception ex)
            {
                var inner = ex is TargetInvocationException tie && tie.InnerException != null ? tie.InnerException : ex;
                var expectedTypeName = FormatExpectedClrType(dataType);
                throw new ArgumentException(
                    $"Failed to set field '{kv.Name}' on component '{compId}' (expected CLR type '{expectedTypeName}'): {inner.Message}",
                    inner);
            }
        }
    }

    private void ApplyWiring(
        string compId,
        Type type,
        object instance,
        JsonElement wiringEl,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        if (wiringEl.ValueKind != JsonValueKind.Object)
            throw new ArgumentException($"wiring on component '{compId}' must be a JSON object.");

        foreach (var kv in wiringEl.EnumerateObject())
        {
            ApplyOneWiringEntry(compId, type, instance, kv.Name, kv.Value, resolveComponent, allSpecs);
        }
    }

    private void ApplyOneWiringEntry(
        string compId,
        Type type,
        object instance,
        string slotName,
        JsonElement valueEl,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        var normSlot = NormalizeKey(slotName);
        var candidateMethods = type.GetMethods(BindingFlags.Public | BindingFlags.Instance)
            .Where(m => !m.IsSpecialName && (m.Name.StartsWith("Set", StringComparison.Ordinal) || m.Name.StartsWith("Add", StringComparison.Ordinal)))
            .ToList();

        MethodInfo? FindMethod(string targetNorm) =>
            candidateMethods.FirstOrDefault(m =>
                NormalizeKey(m.Name) == targetNorm
                || (m.Name.Length > 3 && NormalizeKey(m.Name[3..]) == targetNorm)
                || (m.Name.Length > 3 && NormalizeKey(m.Name[3..] + "s") == targetNorm)
                || (targetNorm.EndsWith("s", StringComparison.Ordinal) && m.Name.Length > 3 && NormalizeKey(m.Name[3..]) == targetNorm[..^1]));

        var matchedMethod = FindMethod(normSlot);
        if (matchedMethod != null)
        {
            if (string.Equals(matchedMethod.Name, "AddEMSSensors", StringComparison.OrdinalIgnoreCase)
                && valueEl.ValueKind == JsonValueKind.Array)
            {
                ApplyEmsSensors(compId, type, instance, valueEl, resolveComponent, allSpecs);
                return;
            }
            if (string.Equals(matchedMethod.Name, "AddEMSInternalVariables", StringComparison.OrdinalIgnoreCase)
                && valueEl.ValueKind == JsonValueKind.Array)
            {
                ApplyEmsInternalVariables(compId, type, instance, valueEl, resolveComponent, allSpecs);
                return;
            }
            if (string.Equals(matchedMethod.Name, "AddEMSActuators", StringComparison.OrdinalIgnoreCase)
                && valueEl.ValueKind == JsonValueKind.Array)
            {
                ApplyEmsActuators(compId, type, instance, valueEl, resolveComponent, allSpecs);
                return;
            }

            var ps = matchedMethod.GetParameters();
            if (ps.Length == 1)
            {
                var paramType = ps[0].ParameterType;
                bool expectsCollection = paramType.IsArray || (paramType.IsGenericType && paramType.GetGenericTypeDefinition() == typeof(List<>));
                if (!expectsCollection && valueEl.ValueKind == JsonValueKind.Array)
                {
                    foreach (var item in valueEl.EnumerateArray())
                    {
                        var arg = CoerceValue(item, paramType, resolveComponent, allSpecs);
                        matchedMethod.Invoke(instance, new[] { arg });
                    }
                }
                else
                {
                    var arg = CoerceValue(valueEl, paramType, resolveComponent, allSpecs);
                    matchedMethod.Invoke(instance, new[] { arg });
                }
                return;
            }
            if (valueEl.ValueKind == JsonValueKind.Array)
            {
                var items = valueEl.EnumerateArray().ToList();
                if (items.Count == ps.Length)
                {
                    var args = new object?[ps.Length];
                    for (int i = 0; i < ps.Length; i++)
                    {
                        args[i] = CoerceValue(items[i], ps[i].ParameterType, resolveComponent, allSpecs);
                    }
                    matchedMethod.Invoke(instance, args);
                    return;
                }
            }
        }

        // Fallback to writable property (e.g. OAStreamObjs, ReliefStreamObjs, AllowMultiAirLoops)
        var matchedProp = type.GetProperties(BindingFlags.Public | BindingFlags.Instance)
            .FirstOrDefault(p => NormalizeKey(p.Name) == normSlot);
        if (matchedProp != null)
        {
            if (matchedProp.CanWrite)
            {
                var val = CoerceValue(valueEl, matchedProp.PropertyType, resolveComponent, allSpecs);
                matchedProp.SetValue(instance, val);
                return;
            }
            if (matchedProp.GetValue(instance) is IList list && valueEl.ValueKind == JsonValueKind.Array)
            {
                var elemType = matchedProp.PropertyType.IsGenericType
                    ? matchedProp.PropertyType.GetGenericArguments()[0]
                    : typeof(object);
                foreach (var item in valueEl.EnumerateArray())
                {
                    list.Add(CoerceValue(item, elemType, resolveComponent, allSpecs));
                }
                return;
            }
        }

        var available = string.Join(", ", candidateMethods.Select(m => m.Name).Distinct());
        throw new ArgumentException($"Unknown wiring slot '{slotName}' on {type.Name} (component '{compId}'). Available methods: {available}");
    }

    private void ApplyOutputVariables(string compId, Type type, object instance, JsonElement outVarsEl)
    {
        var ovType = _runtime.ResolveHvacType("IB_OutputVariable");
        var ctor = ovType.GetConstructors()[0];
        var tsEnumType = ctor.GetParameters()[1].ParameterType;
        var listType = typeof(List<>).MakeGenericType(ovType);
        var list = (IList)Activator.CreateInstance(listType)!;

        foreach (var item in outVarsEl.EnumerateArray())
        {
            string varName;
            string freq = "Hourly";
            if (item.ValueKind == JsonValueKind.String)
            {
                varName = item.GetString()!;
            }
            else if (item.ValueKind == JsonValueKind.Object)
            {
                varName = GetRequiredString(item, "variable_name");
                if (item.TryGetProperty("reporting_frequency", out var fEl) && fEl.ValueKind == JsonValueKind.String)
                {
                    freq = fEl.GetString() ?? "Hourly";
                }
            }
            else
            {
                throw new ArgumentException($"Invalid output_variables entry on '{compId}'.");
            }

            if (!Enum.TryParse(tsEnumType, freq, ignoreCase: true, out var tsVal))
            {
                throw new ArgumentException($"Invalid reporting_frequency '{freq}' on '{compId}'. Valid: {string.Join(", ", Enum.GetNames(tsEnumType))}");
            }
            list.Add(ctor.Invoke(new[] { varName, tsVal }));
        }

        if (list.Count > 0)
        {
            var addOv = type.GetMethod("AddOutputVariables", new[] { listType })
                ?? throw new MissingMethodException($"{type.Name}.AddOutputVariables not found.");
            addOv.Invoke(instance, new object[] { list });
        }
    }

    private void ApplyIbProperties(
        string compId,
        Type type,
        object instance,
        JsonElement ibPropsEl,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        var ibPropsObj = type.GetProperty("IBProperties")?.GetValue(instance);
        if (ibPropsObj is not IDictionary dict)
            throw new ArgumentException($"Component '{compId}' ({type.Name}) does not expose IBProperties dictionary.");

        foreach (var prop in ibPropsEl.EnumerateObject())
        {
            dict[prop.Name] = ConvertJsonValueForProperty(prop.Value, resolveComponent, allSpecs);
        }
    }

    private object? ConvertJsonValueForProperty(
        JsonElement el,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        switch (el.ValueKind)
        {
            case JsonValueKind.Null:
            case JsonValueKind.Undefined:
                return null;
            case JsonValueKind.True:
            case JsonValueKind.False:
                return el.GetBoolean();
            case JsonValueKind.Number:
                return el.TryGetInt32(out var iv) ? iv : el.GetDouble();
            case JsonValueKind.String:
                {
                    var s = el.GetString()!;
                    var stripped = StripRefPrefix(s);
                    if ((s.StartsWith("@", StringComparison.Ordinal) || allSpecs.ContainsKey(stripped))
                        && allSpecs.ContainsKey(stripped))
                    {
                        return resolveComponent(stripped);
                    }
                    return s;
                }
            case JsonValueKind.Array:
                {
                    var items = new List<object?>();
                    foreach (var item in el.EnumerateArray())
                    {
                        items.Add(ConvertJsonValueForProperty(item, resolveComponent, allSpecs));
                    }
                    var nonNull = items.Where(x => x != null).ToList();
                    if (nonNull.Count > 0 && nonNull.All(x => _runtime.ResolveHvacType("IB_HVACObject").IsInstanceOfType(x)))
                    {
                        var hvacListType = typeof(List<>).MakeGenericType(_runtime.ResolveHvacType("IB_HVACObject"));
                        var typed = (IList)Activator.CreateInstance(hvacListType)!;
                        foreach (var x in nonNull) typed.Add(x);
                        return typed;
                    }
                    if (nonNull.Count > 0 && nonNull.All(x => x is double || x is int))
                    {
                        return nonNull.Select(Convert.ToDouble).ToList();
                    }
                    return items;
                }
            default:
                return el.GetRawText();
        }
    }

    private void ApplyChildren(
        string compId,
        Type type,
        object instance,
        JsonElement childrenEl,
        Func<string, object> resolveComponent)
    {
        var childrenObj = type.GetProperty("Children")?.GetValue(instance);
        if (childrenObj is not IList childList)
            throw new ArgumentException($"Component '{compId}' ({type.Name}) does not expose Children list.");

        foreach (var item in childrenEl.EnumerateArray())
        {
            if (item.ValueKind != JsonValueKind.String || string.IsNullOrWhiteSpace(item.GetString()))
                throw new ArgumentException($"children entries on '{compId}' must be component ID strings.");
            var child = resolveComponent(StripRefPrefix(item.GetString()!));
            childList.Add(child);
        }
    }

    private void ApplyOptionalTrackingAndFields(
        string label,
        Type itemType,
        object itemObj,
        JsonElement objEl,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        if (objEl.TryGetProperty("tracking_id", out var tidEl) && tidEl.ValueKind == JsonValueKind.String)
        {
            var tid = tidEl.GetString();
            if (!string.IsNullOrWhiteSpace(tid))
            {
                itemType.GetMethod("SetTrackingID", new[] { typeof(string) })?.Invoke(itemObj, new object[] { tid });
            }
        }
        if (objEl.TryGetProperty("name", out var nameEl) && nameEl.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(nameEl.GetString()))
        {
            SetFieldByName(itemType, itemObj, "Name", nameEl.GetString()!);
        }
        if (objEl.TryGetProperty("fields", out var fieldsEl) && fieldsEl.ValueKind == JsonValueKind.Object)
        {
            ApplyFields(label, itemType, itemObj, fieldsEl, resolveComponent, allSpecs);
        }
    }

    private void ApplyEmsSensors(
        string compId,
        Type type,
        object instance,
        JsonElement sensorsEl,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        var sensorType = _runtime.ResolveHvacType("IB_EnergyManagementSystemSensor");
        var listType = typeof(List<>).MakeGenericType(sensorType);
        var list = (IList)Activator.CreateInstance(listType)!;

        foreach (var item in sensorsEl.EnumerateArray())
        {
            object sensorObj;
            if (item.ValueKind == JsonValueKind.String)
            {
                sensorObj = resolveComponent(StripRefPrefix(item.GetString()!));
                if (!sensorType.IsInstanceOfType(sensorObj))
                    throw new ArgumentException($"ems_sensors item '{item.GetString()}' on '{compId}' is not an IB_EnergyManagementSystemSensor.");
            }
            else if (item.ValueKind == JsonValueKind.Object)
            {
                sensorObj = Activator.CreateInstance(sensorType)!;
                ApplyOptionalTrackingAndFields($"{compId}:ems_sensor", sensorType, sensorObj, item, resolveComponent, allSpecs);
                if (item.TryGetProperty("key_name", out var knEl) && knEl.ValueKind == JsonValueKind.String)
                {
                    sensorType.GetMethod("SetKeyName", new[] { typeof(string) })?.Invoke(sensorObj, new object[] { knEl.GetString()! });
                }
                if (item.TryGetProperty("output_variable", out var ovEl) && ovEl.ValueKind == JsonValueKind.String)
                {
                    sensorType.GetMethod("SetOutputVariable", new[] { typeof(string) })?.Invoke(sensorObj, new object[] { ovEl.GetString()! });
                }
                else if (item.TryGetProperty("output_variable_or_meter_name", out var ovmEl) && ovmEl.ValueKind == JsonValueKind.String)
                {
                    sensorType.GetMethod("SetOutputVariable", new[] { typeof(string) })?.Invoke(sensorObj, new object[] { ovmEl.GetString()! });
                }
            }
            else
            {
                throw new ArgumentException($"Invalid ems_sensors entry on '{compId}'.");
            }
            list.Add(sensorObj);
        }

        if (list.Count > 0)
        {
            var addMethod = type.GetMethod("AddEMSSensors", new[] { listType })
                ?? throw new MissingMethodException($"{type.Name}.AddEMSSensors not found.");
            addMethod.Invoke(instance, new object[] { list });
        }
    }

    private void ApplyEmsInternalVariables(
        string compId,
        Type type,
        object instance,
        JsonElement ivarsEl,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        var ivarType = _runtime.ResolveHvacType("IB_EnergyManagementSystemInternalVariable");
        var listType = typeof(List<>).MakeGenericType(ivarType);
        var list = (IList)Activator.CreateInstance(listType)!;

        foreach (var item in ivarsEl.EnumerateArray())
        {
            object ivarObj;
            if (item.ValueKind == JsonValueKind.String)
            {
                ivarObj = resolveComponent(StripRefPrefix(item.GetString()!));
                if (!ivarType.IsInstanceOfType(ivarObj))
                    throw new ArgumentException($"ems_internal_variables item '{item.GetString()}' on '{compId}' is not an IB_EnergyManagementSystemInternalVariable.");
            }
            else if (item.ValueKind == JsonValueKind.Object)
            {
                ivarObj = Activator.CreateInstance(ivarType)!;
                ApplyOptionalTrackingAndFields($"{compId}:ems_internal_variable", ivarType, ivarObj, item, resolveComponent, allSpecs);
                if (item.TryGetProperty("internal_data_type", out var dtEl) && dtEl.ValueKind == JsonValueKind.String)
                {
                    ivarType.GetMethod("SetInternalDataType", new[] { typeof(string) })?.Invoke(ivarObj, new object[] { dtEl.GetString()! });
                }
                else if (item.TryGetProperty("data_type", out var dt2El) && dt2El.ValueKind == JsonValueKind.String)
                {
                    ivarType.GetMethod("SetInternalDataType", new[] { typeof(string) })?.Invoke(ivarObj, new object[] { dt2El.GetString()! });
                }
                if (item.TryGetProperty("host_obj", out var hostEl) && hostEl.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(hostEl.GetString()))
                {
                    ivarType.GetProperty("HostObj")?.SetValue(ivarObj, resolveComponent(StripRefPrefix(hostEl.GetString()!)));
                }
            }
            else
            {
                throw new ArgumentException($"Invalid ems_internal_variables entry on '{compId}'.");
            }
            list.Add(ivarObj);
        }

        if (list.Count > 0)
        {
            var addMethod = type.GetMethod("AddEMSInternalVariables", new[] { listType })
                ?? throw new MissingMethodException($"{type.Name}.AddEMSInternalVariables not found.");
            addMethod.Invoke(instance, new object[] { list });
        }
    }

    private void ApplyEmsActuators(
        string compId,
        Type type,
        object instance,
        JsonElement actsEl,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        var actType = _runtime.ResolveHvacType("IB_EnergyManagementSystemActuator");
        var modelObjType = _runtime.ResolveHvacType("IB_ModelObject");
        var listType = typeof(List<>).MakeGenericType(actType);
        var list = (IList)Activator.CreateInstance(listType)!;

        foreach (var item in actsEl.EnumerateArray())
        {
            object actObj;
            if (item.ValueKind == JsonValueKind.String)
            {
                actObj = resolveComponent(StripRefPrefix(item.GetString()!));
                if (!actType.IsInstanceOfType(actObj))
                    throw new ArgumentException($"ems_actuators item '{item.GetString()}' on '{compId}' is not an IB_EnergyManagementSystemActuator.");
            }
            else if (item.ValueKind == JsonValueKind.Object)
            {
                if (item.TryGetProperty("actuated_obj", out var aoEl) && aoEl.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(aoEl.GetString()))
                {
                    var aoKey = StripRefPrefix(aoEl.GetString()!);
                    if (allSpecs.ContainsKey(aoKey))
                    {
                        var targetComp = resolveComponent(aoKey);
                        actObj = actType.GetConstructor(new[] { modelObjType })!.Invoke(new[] { targetComp });
                    }
                    else
                    {
                        actObj = actType.GetConstructor(new[] { typeof(string) })!.Invoke(new object[] { aoKey });
                    }
                }
                else
                {
                    actObj = Activator.CreateInstance(actType)!;
                }

                ApplyOptionalTrackingAndFields($"{compId}:ems_actuator", actType, actObj, item, resolveComponent, allSpecs);
                if (item.TryGetProperty("actuated_component_type", out var ctEl) && ctEl.ValueKind == JsonValueKind.String)
                {
                    SetFieldByName(actType, actObj, "ActuatedComponentType", ctEl.GetString()!);
                }
                else if (item.TryGetProperty("component_type", out var ct2El) && ct2El.ValueKind == JsonValueKind.String)
                {
                    SetFieldByName(actType, actObj, "ActuatedComponentType", ct2El.GetString()!);
                }
                if (item.TryGetProperty("actuated_component_control_type", out var ccEl) && ccEl.ValueKind == JsonValueKind.String)
                {
                    SetFieldByName(actType, actObj, "ActuatedComponentControlType", ccEl.GetString()!);
                }
                else if (item.TryGetProperty("control_type", out var cc2El) && cc2El.ValueKind == JsonValueKind.String)
                {
                    SetFieldByName(actType, actObj, "ActuatedComponentControlType", cc2El.GetString()!);
                }
            }
            else
            {
                throw new ArgumentException($"Invalid ems_actuators entry on '{compId}'.");
            }
            list.Add(actObj);
        }

        if (list.Count > 0)
        {
            var addMethod = type.GetMethod("AddEMSActuators", new[] { listType })
                ?? throw new MissingMethodException($"{type.Name}.AddEMSActuators not found.");
            addMethod.Invoke(instance, new object[] { list });
        }
    }

    private object CreateThermalZone(
        string roomName,
        JsonElement tzEl,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        var zoneType = _runtime.ResolveHvacType("IB_ThermalZone");
        var zone = Activator.CreateInstance(zoneType, new object[] { roomName })!;
        var zoneLabel = $"thermal_zone:{roomName}";

        if (tzEl.TryGetProperty("fields", out var fieldsEl) && fieldsEl.ValueKind == JsonValueKind.Object)
        {
            ApplyFields(zoneLabel, zoneType, zone, fieldsEl, resolveComponent, allSpecs);
        }
        if (tzEl.TryGetProperty("sizing_zone", out var szEl) && szEl.ValueKind == JsonValueKind.String)
        {
            var szId = StripRefPrefix(szEl.GetString()!);
            zoneType.GetMethod("SetSizingZone")!.Invoke(zone, new[] { resolveComponent(szId) });
        }
        if (tzEl.TryGetProperty("air_terminal", out var atEl) && atEl.ValueKind == JsonValueKind.String)
        {
            var atId = StripRefPrefix(atEl.GetString()!);
            zoneType.GetMethod("SetAirTerminal")!.Invoke(zone, new[] { resolveComponent(atId) });
        }

        var eqIds = new List<string>();
        if (tzEl.TryGetProperty("zone_equipments", out var eqEl) && eqEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in eqEl.EnumerateArray())
            {
                if (item.ValueKind != JsonValueKind.String)
                    throw new ArgumentException($"zone_equipments entries on room '{roomName}' must be component ID strings.");
                eqIds.Add(StripRefPrefix(item.GetString()!));
            }
        }

        // Parse equipment_list_priorities if present, sort initial ZoneEquipments order and stash metadata on IBProperties
        var priorityMap = ParseEquipmentListPriorities(tzEl, roomName);
        if (priorityMap != null && eqIds.Count > 1)
        {
            eqIds = eqIds
                .Select((eid, idx) => (Id: eid, Idx: idx, Score: priorityMap.TryGetValue(eid, out var pr) ? Math.Min(pr.Cooling, pr.Heating) : int.MaxValue))
                .OrderBy(x => x.Score)
                .ThenBy(x => x.Idx)
                .Select(x => x.Id)
                .ToList();
        }
        if (eqIds.Count > 0)
        {
            var addEq = zoneType.GetMethod("AddZoneEquipment")!;
            foreach (var eid in eqIds)
            {
                addEq.Invoke(zone, new[] { resolveComponent(eid) });
            }
        }
        if (priorityMap != null && priorityMap.Count > 0)
        {
            var resolvedPriorities = new List<Dictionary<string, object?>>();
            foreach (var kv in priorityMap)
            {
                string? trackingTag = null;
                if (allSpecs.ContainsKey(kv.Key))
                {
                    var compObj = resolveComponent(kv.Key);
                    trackingTag = compObj.GetType().GetMethod("GetTrackingTagID")?.Invoke(compObj, null)?.ToString();
                }
                resolvedPriorities.Add(new Dictionary<string, object?>
                {
                    ["component"] = kv.Key,
                    ["tracking_tag"] = trackingTag,
                    ["cooling_priority"] = kv.Value.Cooling,
                    ["heating_priority"] = kv.Value.Heating,
                });
            }
            if (zoneType.GetProperty("IBProperties")?.GetValue(zone) is IDictionary ibProps)
            {
                ibProps["EquipmentListPriorities"] = JsonSerializer.Serialize(resolvedPriorities);
            }
        }

        if (tzEl.TryGetProperty("allow_multi_air_loops", out var amaEl) && (amaEl.ValueKind == JsonValueKind.True || amaEl.ValueKind == JsonValueKind.False))
        {
            zoneType.GetProperty("AllowMultiAirLoops")?.SetValue(zone, amaEl.GetBoolean());
        }
        if (tzEl.TryGetProperty("is_air_terminal_before_zone_equipments", out var atbEl) && (atbEl.ValueKind == JsonValueKind.True || atbEl.ValueKind == JsonValueKind.False))
        {
            zoneType.GetProperty("IsAirTerminalBeforeZoneEquipments")?.SetValue(zone, atbEl.GetBoolean());
        }
        if (tzEl.TryGetProperty("wiring", out var wiringEl) && wiringEl.ValueKind == JsonValueKind.Object)
        {
            ApplyWiring(zoneLabel, zoneType, zone, wiringEl, resolveComponent, allSpecs);
        }
        if (tzEl.TryGetProperty("output_variables", out var outVarsEl) && outVarsEl.ValueKind == JsonValueKind.Array)
        {
            ApplyOutputVariables(zoneLabel, zoneType, zone, outVarsEl);
        }
        if (tzEl.TryGetProperty("ems_sensors", out var sensorsEl) && sensorsEl.ValueKind == JsonValueKind.Array)
        {
            ApplyEmsSensors(zoneLabel, zoneType, zone, sensorsEl, resolveComponent, allSpecs);
        }
        if (tzEl.TryGetProperty("ems_internal_variables", out var ivarsEl) && ivarsEl.ValueKind == JsonValueKind.Array)
        {
            ApplyEmsInternalVariables(zoneLabel, zoneType, zone, ivarsEl, resolveComponent, allSpecs);
        }
        if (tzEl.TryGetProperty("ems_actuators", out var actsEl) && actsEl.ValueKind == JsonValueKind.Array)
        {
            ApplyEmsActuators(zoneLabel, zoneType, zone, actsEl, resolveComponent, allSpecs);
        }
        return zone;
    }

    private void ApplyThermalZonePlenums(
        string roomName,
        object zone,
        JsonElement tzEl,
        Dictionary<string, object> zonesByRoom,
        Func<string, object> resolveComponent)
    {
        var zoneType = zone.GetType();
        if (tzEl.TryGetProperty("supply_plenum", out var spEl) && spEl.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(spEl.GetString()))
        {
            var plenum = ResolvePlenumZone(spEl.GetString()!, zonesByRoom, resolveComponent);
            zoneType.GetMethod("SetSupplyPlenum")!.Invoke(zone, new[] { plenum });
        }
        if (tzEl.TryGetProperty("return_plenum", out var rpEl) && rpEl.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(rpEl.GetString()))
        {
            var plenum = ResolvePlenumZone(rpEl.GetString()!, zonesByRoom, resolveComponent);
            zoneType.GetMethod("SetReturnPlenum")!.Invoke(zone, new[] { plenum });
        }
    }

    private object ResolvePlenumZone(
        string rawRef,
        Dictionary<string, object> zonesByRoom,
        Func<string, object> resolveComponent)
    {
        var key = StripRefPrefix(rawRef);
        if (zonesByRoom.TryGetValue(key, out var existingZone))
            return existingZone;
        try
        {
            var comp = resolveComponent(key);
            if (comp.GetType().Name == "IB_ThermalZone")
                return comp;
        }
        catch (KeyNotFoundException)
        {
        }
        var zoneType = _runtime.ResolveHvacType("IB_ThermalZone");
        return Activator.CreateInstance(zoneType, new object[] { key })!;
    }

    private static Dictionary<string, (int Cooling, int Heating)>? ParseEquipmentListPriorities(
        JsonElement tzEl,
        string roomName)
    {
        if (!tzEl.TryGetProperty("equipment_list_priorities", out var el)
            || el.ValueKind == JsonValueKind.Null
            || el.ValueKind == JsonValueKind.Undefined)
        {
            return null;
        }

        var map = new Dictionary<string, (int Cooling, int Heating)>(StringComparer.Ordinal);
        if (el.ValueKind == JsonValueKind.Object)
        {
            foreach (var prop in el.EnumerateObject())
            {
                var cid = StripRefPrefix(prop.Name);
                if (prop.Value.ValueKind == JsonValueKind.Number)
                {
                    int p = Math.Max(1, prop.Value.GetInt32());
                    map[cid] = (p, p);
                }
                else if (prop.Value.ValueKind == JsonValueKind.Object)
                {
                    int cool = prop.Value.TryGetProperty("cooling_priority", out var cEl) && cEl.ValueKind == JsonValueKind.Number
                        ? Math.Max(1, cEl.GetInt32())
                        : (prop.Value.TryGetProperty("cooling", out var c2El) && c2El.ValueKind == JsonValueKind.Number ? Math.Max(1, c2El.GetInt32()) : 1);
                    int heat = prop.Value.TryGetProperty("heating_priority", out var hEl) && hEl.ValueKind == JsonValueKind.Number
                        ? Math.Max(1, hEl.GetInt32())
                        : (prop.Value.TryGetProperty("heating", out var h2El) && h2El.ValueKind == JsonValueKind.Number ? Math.Max(1, h2El.GetInt32()) : cool);
                    map[cid] = (cool, heat);
                }
                else
                {
                    throw new ArgumentException($"Invalid equipment_list_priorities value for '{prop.Name}' on room '{roomName}'.");
                }
            }
            return map;
        }

        if (el.ValueKind == JsonValueKind.Array)
        {
            int idx = 1;
            foreach (var item in el.EnumerateArray())
            {
                if (item.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(item.GetString()))
                {
                    map[StripRefPrefix(item.GetString()!)] = (idx, idx);
                }
                else if (item.ValueKind == JsonValueKind.Object)
                {
                    var cid = item.TryGetProperty("component", out var compEl) && compEl.ValueKind == JsonValueKind.String
                        ? StripRefPrefix(compEl.GetString()!)
                        : GetRequiredString(item, "id");
                    int cool = item.TryGetProperty("cooling_priority", out var cEl) && cEl.ValueKind == JsonValueKind.Number
                        ? Math.Max(1, cEl.GetInt32())
                        : (item.TryGetProperty("priority", out var pEl) && pEl.ValueKind == JsonValueKind.Number ? Math.Max(1, pEl.GetInt32()) : idx);
                    int heat = item.TryGetProperty("heating_priority", out var hEl) && hEl.ValueKind == JsonValueKind.Number
                        ? Math.Max(1, hEl.GetInt32())
                        : cool;
                    map[cid] = (cool, heat);
                }
                else
                {
                    throw new ArgumentException($"Invalid equipment_list_priorities array item on room '{roomName}'.");
                }
                idx++;
            }
            return map;
        }

        throw new ArgumentException($"equipment_list_priorities on room '{roomName}' must be an object or array.");
    }

    private void ApplyLoopCommon(
        string loopLabel,
        Type loopType,
        object loopInst,
        JsonElement loopEl,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        if (loopEl.TryGetProperty("fields", out var fieldsEl) && fieldsEl.ValueKind == JsonValueKind.Object)
        {
            ApplyFields(loopLabel, loopType, loopInst, fieldsEl, resolveComponent, allSpecs);
        }
        if (loopEl.TryGetProperty("name", out var nameEl) && nameEl.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(nameEl.GetString()))
        {
            SetFieldByName(loopType, loopInst, "Name", nameEl.GetString()!);
        }
        if (loopEl.TryGetProperty("availability_managers", out var amEl) && amEl.ValueKind == JsonValueKind.Array)
        {
            var amlObj = BuildAvailabilityManagerList(loopLabel, amEl, resolveComponent, allSpecs);
            if (amlObj != null)
            {
                SetFieldByName(loopType, loopInst, "AvailabilityManagers", amlObj);
            }
        }
        if (loopEl.TryGetProperty("wiring", out var wiringEl) && wiringEl.ValueKind == JsonValueKind.Object)
        {
            ApplyWiring(loopLabel, loopType, loopInst, wiringEl, resolveComponent, allSpecs);
        }
        if (loopEl.TryGetProperty("output_variables", out var outVarsEl) && outVarsEl.ValueKind == JsonValueKind.Array)
        {
            ApplyOutputVariables(loopLabel, loopType, loopInst, outVarsEl);
        }
        if (loopEl.TryGetProperty("ems_sensors", out var sensorsEl) && sensorsEl.ValueKind == JsonValueKind.Array)
        {
            ApplyEmsSensors(loopLabel, loopType, loopInst, sensorsEl, resolveComponent, allSpecs);
        }
        if (loopEl.TryGetProperty("ems_internal_variables", out var ivarsEl) && ivarsEl.ValueKind == JsonValueKind.Array)
        {
            ApplyEmsInternalVariables(loopLabel, loopType, loopInst, ivarsEl, resolveComponent, allSpecs);
        }
        if (loopEl.TryGetProperty("ems_actuators", out var actsEl) && actsEl.ValueKind == JsonValueKind.Array)
        {
            ApplyEmsActuators(loopLabel, loopType, loopInst, actsEl, resolveComponent, allSpecs);
        }
    }

    private object? BuildAvailabilityManagerList(
        string loopLabel,
        JsonElement amEl,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        var amBaseType = _runtime.ResolveHvacType("IB_AvailabilityManager");
        var listType = typeof(List<>).MakeGenericType(amBaseType);
        var managers = (IList)Activator.CreateInstance(listType)!;

        foreach (var item in amEl.EnumerateArray())
        {
            object mgr;
            if (item.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(item.GetString()))
            {
                mgr = resolveComponent(StripRefPrefix(item.GetString()!));
            }
            else if (item.ValueKind == JsonValueKind.Object)
            {
                mgr = InstantiateComponent($"{loopLabel}:availability_manager", item, resolveComponent, allSpecs);
            }
            else
            {
                throw new ArgumentException($"availability_managers entries on {loopLabel} must be component IDs or component spec objects.");
            }
            if (!amBaseType.IsInstanceOfType(mgr))
            {
                throw new ArgumentException($"Availability manager '{mgr.GetType().Name}' on {loopLabel} does not inherit from IB_AvailabilityManager.");
            }
            managers.Add(mgr);
        }

        if (managers.Count == 0) return null;

        var amlType = _runtime.ResolveHvacType("IB_AvailabilityManagerList");
        var aml = Activator.CreateInstance(amlType)!;
        amlType.GetMethod("SetManagers", new[] { listType })!.Invoke(aml, new object[] { managers });
        return aml;
    }

    private object BuildAirLoop(
        JsonElement alEl,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs,
        Dictionary<string, object> zonesByRoom,
        HashSet<string> assignedZoneRooms)
    {
        var alType = _runtime.ResolveHvacType("IB_AirLoopHVAC");
        var airLoop = Activator.CreateInstance(alType)!;
        var loopName = alEl.TryGetProperty("name", out var nEl) && nEl.ValueKind == JsonValueKind.String
            ? nEl.GetString() ?? "AirLoop"
            : "AirLoop";

        ApplyLoopCommon($"air_loop:{loopName}", alType, airLoop, alEl, resolveComponent, allSpecs);

        if (alEl.TryGetProperty("sizing_system", out var szEl) && szEl.ValueKind == JsonValueKind.String)
        {
            alType.GetMethod("SetSizingSystem")!.Invoke(airLoop, new[] { resolveComponent(StripRefPrefix(szEl.GetString()!)) });
        }

        // Parse optional return_path (return fan/components before OA system, relief_stream_objs, and/or return_plenum)
        var returnPreSupply = new List<object>();
        var reliefStreamComps = new List<object>();
        string? loopReturnPlenumRef = null;
        if (alEl.TryGetProperty("return_path", out var rpEl) && rpEl.ValueKind != JsonValueKind.Null && rpEl.ValueKind != JsonValueKind.Undefined)
        {
            if (rpEl.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(rpEl.GetString()))
            {
                var key = StripRefPrefix(rpEl.GetString()!);
                if (allSpecs.ContainsKey(key) && resolveComponent(key).GetType().Name != "IB_ThermalZone")
                    returnPreSupply.Add(resolveComponent(key));
                else
                    loopReturnPlenumRef = key;
            }
            else if (rpEl.ValueKind == JsonValueKind.Array)
            {
                foreach (var item in rpEl.EnumerateArray())
                {
                    if (item.ValueKind != JsonValueKind.String || string.IsNullOrWhiteSpace(item.GetString()))
                        throw new ArgumentException("air_loops[].return_path array items must be component ID strings.");
                    returnPreSupply.Add(resolveComponent(StripRefPrefix(item.GetString()!)));
                }
            }
            else if (rpEl.ValueKind == JsonValueKind.Object)
            {
                if (rpEl.TryGetProperty("return_plenum", out var rplEl) && rplEl.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(rplEl.GetString()))
                    loopReturnPlenumRef = rplEl.GetString()!;
                else if (rpEl.TryGetProperty("plenum", out var plmEl) && plmEl.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(plmEl.GetString()))
                    loopReturnPlenumRef = plmEl.GetString()!;

                if (rpEl.TryGetProperty("return_fan", out var rfEl) && rfEl.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(rfEl.GetString()))
                    returnPreSupply.Add(resolveComponent(StripRefPrefix(rfEl.GetString()!)));
                else if (rpEl.TryGetProperty("fan", out var fEl) && fEl.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(fEl.GetString()))
                    returnPreSupply.Add(resolveComponent(StripRefPrefix(fEl.GetString()!)));

                foreach (var key in new[] { "components", "return_components" })
                {
                    if (rpEl.TryGetProperty(key, out var compsEl) && compsEl.ValueKind == JsonValueKind.Array)
                    {
                        foreach (var c in compsEl.EnumerateArray())
                        {
                            if (c.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(c.GetString()))
                                returnPreSupply.Add(resolveComponent(StripRefPrefix(c.GetString()!)));
                        }
                    }
                }
                foreach (var key in new[] { "relief_stream_objs", "relief_components" })
                {
                    if (rpEl.TryGetProperty(key, out var relEl) && relEl.ValueKind == JsonValueKind.Array)
                    {
                        foreach (var c in relEl.EnumerateArray())
                        {
                            if (c.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(c.GetString()))
                                reliefStreamComps.Add(resolveComponent(StripRefPrefix(c.GetString()!)));
                        }
                    }
                }
            }
            else
            {
                throw new ArgumentException("air_loops[].return_path must be a string, list of component IDs, or object.");
            }
        }

        var addToSupply = alType.GetMethod("AddToSupplySide")!;
        var addedSupplyObjs = new List<object>();
        foreach (var preComp in returnPreSupply)
        {
            addToSupply.Invoke(airLoop, new[] { preComp });
            addedSupplyObjs.Add(preComp);
        }

        if (alEl.TryGetProperty("supply", out var supEl) && supEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in supEl.EnumerateArray())
            {
                if (item.ValueKind != JsonValueKind.String)
                    throw new ArgumentException("air_loops[].supply items must be component ID strings.");
                var comp = resolveComponent(StripRefPrefix(item.GetString()!));
                if (reliefStreamComps.Count > 0 && comp.GetType().Name == "IB_OutdoorAirSystem")
                {
                    if (comp.GetType().GetProperty("ReliefStreamObjs")?.GetValue(comp) is IList relList)
                    {
                        foreach (var rc in reliefStreamComps) relList.Add(rc);
                    }
                }
                addToSupply.Invoke(airLoop, new[] { comp });
                addedSupplyObjs.Add(comp);
            }
        }

        if (alEl.TryGetProperty("supply_branches", out var sbEl) && sbEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var branchEl in sbEl.EnumerateArray())
            {
                if (branchEl.ValueKind != JsonValueKind.Array)
                    throw new ArgumentException("air_loops[].supply_branches must be a list of component ID lists.");
                foreach (var item in branchEl.EnumerateArray())
                {
                    if (item.ValueKind != JsonValueKind.String)
                        throw new ArgumentException("air_loops[].supply_branches items must be component ID strings.");
                    var comp = resolveComponent(StripRefPrefix(item.GetString()!));
                    if (reliefStreamComps.Count > 0 && comp.GetType().Name == "IB_OutdoorAirSystem")
                    {
                        if (comp.GetType().GetProperty("ReliefStreamObjs")?.GetValue(comp) is IList relList)
                        {
                            foreach (var rc in reliefStreamComps) relList.Add(rc);
                        }
                    }
                    addToSupply.Invoke(airLoop, new[] { comp });
                    addedSupplyObjs.Add(comp);
                }
            }
        }

        if (reliefStreamComps.Count > 0 && !addedSupplyObjs.Any(o => o.GetType().Name == "IB_OutdoorAirSystem"))
        {
            throw new ArgumentException($"air_loops[].return_path specified relief components on '{loopName}', but no IB_OutdoorAirSystem was found on supply.");
        }

        object GetOrCreateZoneByRoom(string roomOrCompId)
        {
            var key = StripRefPrefix(roomOrCompId);
            if (zonesByRoom.TryGetValue(key, out var z))
            {
                assignedZoneRooms.Add(key);
                return z;
            }
            try
            {
                var comp = resolveComponent(key);
                if (comp.GetType().Name == "IB_ThermalZone") return comp;
            }
            catch (KeyNotFoundException)
            {
                // Auto-create bare IB_ThermalZone for the room name
            }
            var zoneType = _runtime.ResolveHvacType("IB_ThermalZone");
            var created = Activator.CreateInstance(zoneType, new object[] { key })!;
            zonesByRoom[key] = created;
            assignedZoneRooms.Add(key);
            return created;
        }

        var loopZones = new List<object>();
        var addToDemand = alType.GetMethod("AddToDemandSide")!;
        var hvacObjBase = _runtime.ResolveHvacType("IB_HVACObject");
        var airBranchesType = _runtime.ResolveHvacType("IB_AirLoopBranches");
        var addBranchMethod = airBranchesType.GetMethod("AddBranch")!;

        if (alEl.TryGetProperty("demand_branches", out var dbEl) && dbEl.ValueKind == JsonValueKind.Array)
        {
            var ab = Activator.CreateInstance(airBranchesType)!;
            foreach (var branchEl in dbEl.EnumerateArray())
            {
                if (branchEl.ValueKind != JsonValueKind.Array)
                    throw new ArgumentException("air_loops[].demand_branches must be a list of branch lists.");
                var items = branchEl.EnumerateArray().Select(x => GetOrCreateZoneByRoom(x.GetString()!)).ToArray();
                loopZones.AddRange(items);
                var arr = Array.CreateInstance(hvacObjBase, items.Length);
                for (int i = 0; i < items.Length; i++) arr.SetValue(items[i], i);
                addBranchMethod.Invoke(ab, new object[] { arr });
            }
            addToDemand.Invoke(airLoop, new[] { ab });
        }
        else if (alEl.TryGetProperty("demand_zones", out var dzEl) && dzEl.ValueKind == JsonValueKind.Array)
        {
            var ab = Activator.CreateInstance(airBranchesType)!;
            foreach (var zEl in dzEl.EnumerateArray())
            {
                if (zEl.ValueKind != JsonValueKind.String)
                    throw new ArgumentException("air_loops[].demand_zones items must be room name strings.");
                var zoneObj = GetOrCreateZoneByRoom(zEl.GetString()!);
                loopZones.Add(zoneObj);
                var arr = Array.CreateInstance(hvacObjBase, 1);
                arr.SetValue(zoneObj, 0);
                addBranchMethod.Invoke(ab, new object[] { arr });
            }
            addToDemand.Invoke(airLoop, new[] { ab });
        }

        if (!string.IsNullOrWhiteSpace(loopReturnPlenumRef))
        {
            var plenumObj = ResolvePlenumZone(loopReturnPlenumRef, zonesByRoom, resolveComponent);
            foreach (var zObj in loopZones)
            {
                var zt = zObj.GetType();
                if (zt.GetProperty("ReturnPlenum")?.GetValue(zObj) == null)
                {
                    zt.GetMethod("SetReturnPlenum")?.Invoke(zObj, new[] { plenumObj });
                }
            }
        }

        return airLoop;
    }

    private object BuildPlantLoop(
        JsonElement plEl,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        var plType = _runtime.ResolveHvacType("IB_PlantLoop");
        var plantLoop = Activator.CreateInstance(plType)!;
        var loopName = plEl.TryGetProperty("name", out var nEl) && nEl.ValueKind == JsonValueKind.String
            ? nEl.GetString() ?? "PlantLoop"
            : "PlantLoop";

        ApplyLoopCommon($"plant_loop:{loopName}", plType, plantLoop, plEl, resolveComponent, allSpecs);

        // SizingPlant
        if (plEl.TryGetProperty("sizing_plant", out var spEl) && spEl.ValueKind == JsonValueKind.String)
        {
            plType.GetMethod("SetSizingPlant")!.Invoke(plantLoop, new[] { resolveComponent(StripRefPrefix(spEl.GetString()!)) });
        }
        else
        {
            var spType = _runtime.ResolveHvacType("IB_SizingPlant");
            var sp = Activator.CreateInstance(spType)!;
            bool hasSp = false;
            if (plEl.TryGetProperty("loop_type", out var ltEl) && ltEl.ValueKind == JsonValueKind.String)
            {
                SetFieldByName(spType, sp, "LoopType", ltEl.GetString()!);
                hasSp = true;
            }
            if (plEl.TryGetProperty("design_loop_exit_temperature", out var dtEl) && dtEl.ValueKind == JsonValueKind.Number)
            {
                SetFieldByName(spType, sp, "DesignLoopExitTemperature", dtEl.GetDouble());
                hasSp = true;
            }
            if (plEl.TryGetProperty("loop_design_temperature_difference", out var tdEl) && tdEl.ValueKind == JsonValueKind.Number)
            {
                SetFieldByName(spType, sp, "LoopDesignTemperatureDifference", tdEl.GetDouble());
                hasSp = true;
            }
            if (hasSp)
            {
                plType.GetMethod("SetSizingPlant")!.Invoke(plantLoop, new[] { sp });
            }
        }

        if (plEl.TryGetProperty("operation_scheme", out var osEl) && osEl.ValueKind == JsonValueKind.String)
        {
            plType.GetMethod("SetOperationScheme")!.Invoke(plantLoop, new[] { resolveComponent(StripRefPrefix(osEl.GetString()!)) });
        }

        var (supplyBypassPipe, demandBypassPipe) = ResolvePlantBypassPipes(plEl, resolveComponent);

        var addToSupply = plType.GetMethod("AddToSupply")!;
        var addToDemand = plType.GetMethod("AddToDemand")!;

        object BuildPlantBranches(JsonElement branchesEl, string sideName, object? extraBypassPipe)
        {
            var hvacObjBase = _runtime.ResolveHvacType("IB_HVACObject");
            var plBranchesType = _runtime.ResolveHvacType("IB_PlantLoopBranches");
            var branches = Activator.CreateInstance(plBranchesType)!;
            var addBranch = plBranchesType.GetMethod("AddBranch")!;
            foreach (var bEl in branchesEl.EnumerateArray())
            {
                if (bEl.ValueKind != JsonValueKind.Array)
                    throw new ArgumentException($"plant_loops[].{sideName} must be a list of branch lists (e.g. [[\"chiller1\"]]).");
                var comps = bEl.EnumerateArray().Select(c =>
                {
                    if (c.ValueKind != JsonValueKind.String)
                        throw new ArgumentException($"Branch items in plant_loops[].{sideName} must be component ID strings.");
                    return resolveComponent(StripRefPrefix(c.GetString()!));
                }).ToArray();
                var arr = Array.CreateInstance(hvacObjBase, comps.Length);
                for (int i = 0; i < comps.Length; i++) arr.SetValue(comps[i], i);
                addBranch.Invoke(branches, new object[] { arr });
            }
            if (extraBypassPipe != null)
            {
                var bpArr = Array.CreateInstance(hvacObjBase, 1);
                bpArr.SetValue(extraBypassPipe, 0);
                addBranch.Invoke(branches, new object[] { bpArr });
            }
            return branches;
        }

        object BuildSingleBypassBranch(object bypassPipe)
        {
            var hvacObjBase = _runtime.ResolveHvacType("IB_HVACObject");
            var plBranchesType = _runtime.ResolveHvacType("IB_PlantLoopBranches");
            var branches = Activator.CreateInstance(plBranchesType)!;
            var arr = Array.CreateInstance(hvacObjBase, 1);
            arr.SetValue(bypassPipe, 0);
            plBranchesType.GetMethod("AddBranch")!.Invoke(branches, new object[] { arr });
            return branches;
        }

        bool supplyBypassAdded = false;
        if (plEl.TryGetProperty("supply", out var supEl) && supEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in supEl.EnumerateArray())
            {
                if (item.ValueKind == JsonValueKind.String)
                {
                    addToSupply.Invoke(plantLoop, new[] { resolveComponent(StripRefPrefix(item.GetString()!)) });
                }
                else if (item.ValueKind == JsonValueKind.Array)
                {
                    bool attachHere = supplyBypassPipe != null && !supplyBypassAdded && !plEl.TryGetProperty("supply_branches", out _);
                    addToSupply.Invoke(plantLoop, new[] { BuildPlantBranches(item, "supply", attachHere ? supplyBypassPipe : null) });
                    if (attachHere) supplyBypassAdded = true;
                }
                else
                {
                    throw new ArgumentException("plant_loops[].supply items must be component IDs or branch lists.");
                }
            }
        }
        if (plEl.TryGetProperty("supply_branches", out var sbEl) && sbEl.ValueKind == JsonValueKind.Array)
        {
            addToSupply.Invoke(plantLoop, new[] { BuildPlantBranches(sbEl, "supply_branches", supplyBypassPipe) });
            supplyBypassAdded = true;
        }
        if (supplyBypassPipe != null && !supplyBypassAdded)
        {
            addToSupply.Invoke(plantLoop, new[] { BuildSingleBypassBranch(supplyBypassPipe) });
        }

        if (plEl.TryGetProperty("supply_setpoint_manager", out var spmEl) && spmEl.ValueKind == JsonValueKind.String)
        {
            addToSupply.Invoke(plantLoop, new[] { resolveComponent(StripRefPrefix(spmEl.GetString()!)) });
        }
        else if (plEl.TryGetProperty("supply_setpoint", out var spNumEl) && spNumEl.ValueKind == JsonValueKind.Number)
        {
            var spmType = _runtime.ResolveHvacType("IB_SetpointManagerScheduled");
            var spm = Activator.CreateInstance(spmType, new object[] { spNumEl.GetDouble() })!;
            addToSupply.Invoke(plantLoop, new[] { spm });
        }

        bool demandBypassAdded = false;
        if (plEl.TryGetProperty("demand", out var demEl) && demEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in demEl.EnumerateArray())
            {
                if (item.ValueKind == JsonValueKind.String)
                {
                    addToDemand.Invoke(plantLoop, new[] { resolveComponent(StripRefPrefix(item.GetString()!)) });
                }
                else if (item.ValueKind == JsonValueKind.Array)
                {
                    bool attachHere = demandBypassPipe != null && !demandBypassAdded && !plEl.TryGetProperty("demand_branches", out _);
                    addToDemand.Invoke(plantLoop, new[] { BuildPlantBranches(item, "demand", attachHere ? demandBypassPipe : null) });
                    if (attachHere) demandBypassAdded = true;
                }
                else
                {
                    throw new ArgumentException("plant_loops[].demand items must be component IDs or branch lists.");
                }
            }
        }
        if (plEl.TryGetProperty("demand_branches", out var dbEl) && dbEl.ValueKind == JsonValueKind.Array)
        {
            addToDemand.Invoke(plantLoop, new[] { BuildPlantBranches(dbEl, "demand_branches", demandBypassPipe) });
            demandBypassAdded = true;
        }
        if (demandBypassPipe != null && !demandBypassAdded)
        {
            addToDemand.Invoke(plantLoop, new[] { BuildSingleBypassBranch(demandBypassPipe) });
        }

        return plantLoop;
    }

    private (object? SupplyBypass, object? DemandBypass) ResolvePlantBypassPipes(
        JsonElement plEl,
        Func<string, object> resolveComponent)
    {
        if (!plEl.TryGetProperty("bypass_pipes", out var bpEl)
            || bpEl.ValueKind == JsonValueKind.Null
            || bpEl.ValueKind == JsonValueKind.Undefined)
        {
            return (null, null);
        }

        var pipeType = _runtime.ResolveHvacType("IB_PipeAdiabatic");
        object NewPipe() => Activator.CreateInstance(pipeType)!;

        if (bpEl.ValueKind == JsonValueKind.False) return (null, null);
        if (bpEl.ValueKind == JsonValueKind.True) return (NewPipe(), NewPipe());
        if (bpEl.ValueKind == JsonValueKind.String)
        {
            var val = bpEl.GetString()!.Trim();
            if (string.Equals(val, "both", StringComparison.OrdinalIgnoreCase)) return (NewPipe(), NewPipe());
            if (string.Equals(val, "supply", StringComparison.OrdinalIgnoreCase)) return (NewPipe(), null);
            if (string.Equals(val, "demand", StringComparison.OrdinalIgnoreCase)) return (null, NewPipe());
            if (string.Equals(val, "none", StringComparison.OrdinalIgnoreCase)) return (null, null);
            return (resolveComponent(StripRefPrefix(val)), null);
        }
        if (bpEl.ValueKind == JsonValueKind.Array)
        {
            var items = bpEl.EnumerateArray().Where(x => x.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(x.GetString())).ToList();
            object? sPipe = items.Count > 0 ? resolveComponent(StripRefPrefix(items[0].GetString()!)) : null;
            object? dPipe = items.Count > 1 ? resolveComponent(StripRefPrefix(items[1].GetString()!)) : null;
            return (sPipe, dPipe);
        }
        if (bpEl.ValueKind == JsonValueKind.Object)
        {
            object? ParseSide(string key)
            {
                if (!bpEl.TryGetProperty(key, out var sEl) || sEl.ValueKind == JsonValueKind.Null || sEl.ValueKind == JsonValueKind.False)
                    return null;
                if (sEl.ValueKind == JsonValueKind.True) return NewPipe();
                if (sEl.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(sEl.GetString()))
                    return resolveComponent(StripRefPrefix(sEl.GetString()!));
                throw new ArgumentException($"plant_loops[].bypass_pipes.{key} must be boolean or component ID string.");
            }
            return (ParseSide("supply"), ParseSide("demand"));
        }

        throw new ArgumentException("plant_loops[].bypass_pipes must be boolean, string, list, or object.");
    }

    private object BuildVrfSystem(JsonElement vrfEl, Func<string, object> resolveComponent)
    {
        var vrfId = GetRequiredString(vrfEl, "vrf");
        var vrfObj = resolveComponent(StripRefPrefix(vrfId));
        var addTerm = vrfObj.GetType().GetMethod("AddTerminal")
            ?? throw new ArgumentException($"Component '{vrfId}' ({vrfObj.GetType().Name}) does not support AddTerminal.");

        if (vrfEl.TryGetProperty("terminals", out var termsEl) && termsEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var t in termsEl.EnumerateArray())
            {
                if (t.ValueKind != JsonValueKind.String)
                    throw new ArgumentException("vrf_systems[].terminals items must be component ID strings.");
                addTerm.Invoke(vrfObj, new[] { resolveComponent(StripRefPrefix(t.GetString()!)) });
            }
        }
        return vrfObj;
    }

    private void SetFieldByName(Type type, object instance, string fieldName, object value)
    {
        var fsType = _runtime.ResolveFieldSetType(type);
        var fsInst = fsType != null ? _runtime.GetFieldSetInstance(fsType) : null;
        if (fsType == null || fsInst == null) return;

        object? ibField = null;
        if (fsInst is IEnumerable en)
        {
            foreach (var item in en)
            {
                var fn = item?.GetType().GetProperty("FullName")?.GetValue(item)?.ToString();
                if (string.Equals(fn, fieldName, StringComparison.OrdinalIgnoreCase))
                {
                    ibField = item;
                    break;
                }
            }
        }
        if (ibField == null)
            throw new ArgumentException($"Field '{fieldName}' not found on {type.Name}.");

        var ca = type.GetProperty("CustomAttributes")!.GetValue(instance)!;
        var ibFieldType = _runtime.ResolveHvacType("IB_Field");
        ca.GetType().GetMethod("TryAdd", new[] { ibFieldType, typeof(object) })!.Invoke(ca, new[] { ibField, value });
    }

    private static string FormatExpectedClrType(Type? targetType)
    {
        if (targetType == null) return "unknown";
        var underlying = Nullable.GetUnderlyingType(targetType) ?? targetType;
        return underlying.FullName ?? underlying.Name;
    }

    private static string BuildModelObjectFieldHint(string expectedTypeName, bool expectsModelObj)
    {
        if (expectedTypeName.Contains("Schedule", StringComparison.OrdinalIgnoreCase))
        {
            return "Define a separate IB_ScheduleRuleset/IB_ScheduleConstant/IB_ScheduleFile component via IB_Upsert_Components "
                + "and reference it via \"@<schedule_component_id>\" (or a reference wrapper {\"ref\": \"<schedule_component_id>\"}), "
                + "or omit the field to use the default.";
        }
        if (expectsModelObj)
        {
            return $"Define a separate Ironbug component matching '{expectedTypeName}' (e.g. IB_ScheduleRuleset/IB_ScheduleConstant/IB_ScheduleFile for schedules, or IB_Curve* for curves) "
                + "via IB_Upsert_Components and reference it via \"@<component_id>\" (or {\"ref\": \"<component_id>\"}), "
                + "or omit the field to use the default.";
        }
        return $"Pass a scalar value matching '{expectedTypeName}', or reference a defined component via \"@<component_id>\" "
            + "(e.g. define a separate IB_ScheduleRuleset/IB_ScheduleConstant/IB_ScheduleFile component for schedule fields).";
    }

    private object? CoerceFieldValue(
        string compId,
        string fieldName,
        JsonElement el,
        Type? targetType,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        if (el.ValueKind == JsonValueKind.Null) return null;

        var underlyingTarget = targetType != null ? (Nullable.GetUnderlyingType(targetType) ?? targetType) : null;
        var expectedTypeName = FormatExpectedClrType(targetType);
        bool expectsModelObj = underlyingTarget != null
            && underlyingTarget.Namespace != null
            && underlyingTarget.Namespace.StartsWith("OpenStudio", StringComparison.Ordinal);

        if (el.ValueKind == JsonValueKind.Object)
        {
            foreach (var refKey in new[] { "ref", "component_id", "identifier" })
            {
                if (el.TryGetProperty(refKey, out var refEl)
                    && refEl.ValueKind == JsonValueKind.String
                    && !string.IsNullOrWhiteSpace(refEl.GetString()))
                {
                    var refId = StripRefPrefix(refEl.GetString()!);
                    if (allSpecs.ContainsKey(refId))
                    {
                        return resolveComponent(refId);
                    }
                }
            }

            throw new ArgumentException(
                $"Unsupported object value for field '{fieldName}' on component '{compId}' (expected CLR type '{expectedTypeName}'). "
                + BuildModelObjectFieldHint(expectedTypeName, expectsModelObj));
        }

        if (el.ValueKind == JsonValueKind.String)
        {
            var s = el.GetString()!;
            var stripped = StripRefPrefix(s);
            bool explicitRef = s.StartsWith("@", StringComparison.Ordinal);
            if ((explicitRef || expectsModelObj) && allSpecs.ContainsKey(stripped))
            {
                return resolveComponent(stripped);
            }
            if (explicitRef)
            {
                throw new ArgumentException(
                    $"Field '{fieldName}' on component '{compId}' references unknown component '{stripped}' (expected CLR type '{expectedTypeName}'). "
                    + BuildModelObjectFieldHint(expectedTypeName, expectsModelObj));
            }
            if (expectsModelObj)
            {
                throw new ArgumentException(
                    $"Field '{fieldName}' on component '{compId}' expects CLR type '{expectedTypeName}', not string '{s}'. "
                    + BuildModelObjectFieldHint(expectedTypeName, expectsModelObj));
            }
            if (underlyingTarget == typeof(double) && double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var d))
                return d;
            if (underlyingTarget == typeof(int) && int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var iv))
                return iv;
            if (underlyingTarget == typeof(bool) && bool.TryParse(s, out var bv))
                return bv;
            return s;
        }

        if (el.ValueKind == JsonValueKind.Number)
        {
            if (expectsModelObj)
            {
                throw new ArgumentException(
                    $"Field '{fieldName}' on component '{compId}' expects CLR type '{expectedTypeName}', not number '{el.GetRawText()}'. "
                    + BuildModelObjectFieldHint(expectedTypeName, expectsModelObj));
            }
            if (underlyingTarget == typeof(int)) return el.GetInt32();
            return el.GetDouble();
        }
        if (el.ValueKind == JsonValueKind.True || el.ValueKind == JsonValueKind.False)
        {
            if (expectsModelObj)
            {
                throw new ArgumentException(
                    $"Field '{fieldName}' on component '{compId}' expects CLR type '{expectedTypeName}', not boolean '{el.GetBoolean()}'. "
                    + BuildModelObjectFieldHint(expectedTypeName, expectsModelObj));
            }
            return el.GetBoolean();
        }
        throw new ArgumentException(
            $"Unsupported field value kind '{el.ValueKind}' for field '{fieldName}' on component '{compId}' (expected CLR type '{expectedTypeName}'). "
            + BuildModelObjectFieldHint(expectedTypeName, expectsModelObj));
    }

    private object? CoerceValue(
        JsonElement el,
        Type targetType,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        if (el.ValueKind == JsonValueKind.Null) return null;
        var underlying = Nullable.GetUnderlyingType(targetType) ?? targetType;

        if (underlying.IsEnum)
        {
            if (el.ValueKind == JsonValueKind.String && Enum.TryParse(underlying, el.GetString(), ignoreCase: true, out var ev))
                return ev;
            if (el.ValueKind == JsonValueKind.Number)
                return Enum.ToObject(underlying, el.GetInt32());
            throw new ArgumentException($"Invalid enum value for {underlying.Name}: {el}");
        }

        if (underlying == typeof(string))
        {
            return el.ValueKind == JsonValueKind.String ? el.GetString() : el.ToString();
        }
        if (underlying == typeof(double) || underlying == typeof(float))
        {
            var d = el.ValueKind == JsonValueKind.Number
                ? el.GetDouble()
                : double.Parse(el.GetString()!, CultureInfo.InvariantCulture);
            return underlying == typeof(float) ? (float)d : d;
        }
        if (underlying == typeof(int) || underlying == typeof(long))
        {
            var i = el.ValueKind == JsonValueKind.Number
                ? el.GetInt32()
                : int.Parse(el.GetString()!, CultureInfo.InvariantCulture);
            return underlying == typeof(long) ? (long)i : i;
        }
        if (underlying == typeof(bool))
        {
            return el.ValueKind is JsonValueKind.True or JsonValueKind.False
                ? el.GetBoolean()
                : bool.Parse(el.GetString()!);
        }

        if (underlying.IsArray && el.ValueKind == JsonValueKind.Array)
        {
            var elemType = underlying.GetElementType()!;
            var raw = el.EnumerateArray().ToList();
            var arr = Array.CreateInstance(elemType, raw.Count);
            for (int i = 0; i < raw.Count; i++)
            {
                arr.SetValue(CoerceValue(raw[i], elemType, resolveComponent, allSpecs), i);
            }
            return arr;
        }

        if (underlying.IsGenericType && underlying.GetGenericTypeDefinition() == typeof(List<>) && el.ValueKind == JsonValueKind.Array)
        {
            var elemType = underlying.GetGenericArguments()[0];
            var list = (IList)Activator.CreateInstance(underlying)!;
            foreach (var item in el.EnumerateArray())
            {
                list.Add(CoerceValue(item, elemType, resolveComponent, allSpecs));
            }
            return list;
        }

        if (el.ValueKind == JsonValueKind.String)
        {
            var comp = resolveComponent(StripRefPrefix(el.GetString()!));
            if (!underlying.IsInstanceOfType(comp))
            {
                throw new ArgumentException($"Component '{el.GetString()}' ({comp.GetType().Name}) is not assignable to expected type {underlying.Name}.");
            }
            return comp;
        }

        throw new ArgumentException($"Cannot convert JSON {el.ValueKind} to {underlying.Name}.");
    }

    public Dictionary<string, object?> ReverseParse(string specificationJson)
    {
        var sysType = _runtime.ResolveHvacType("IB_HVACSystem");
        var fromJsonMethod = sysType.GetMethod("FromJson", BindingFlags.Public | BindingFlags.Static)!;
        var sys = fromJsonMethod.Invoke(null, new object[] { specificationJson })
            ?? throw new InvalidOperationException("IB_HVACSystem.FromJson returned null.");

        var ctx = new ReverseParseContext(this);
        var draft = ctx.ParseSystem(sysType, sys);
        var summary = SummarizeSystem(sysType, sys);
        return new Dictionary<string, object?>
        {
            ["draft"] = draft,
            ["summary"] = summary,
            ["warnings"] = ctx.Warnings,
        };
    }

    private sealed class ReverseParseContext
    {
        private readonly SystemBuilder _owner;
        private readonly Dictionary<string, Dictionary<string, object?>> _components = new(StringComparer.Ordinal);
        private readonly Dictionary<string, string> _trackingToId = new(StringComparer.OrdinalIgnoreCase);
        private readonly Dictionary<object, string> _objToId = new(ReferenceEqualityComparer.Instance);
        private readonly Dictionary<string, int> _counters = new(StringComparer.OrdinalIgnoreCase);
        private readonly Dictionary<string, Dictionary<string, object?>> _zonesByRoom = new(StringComparer.Ordinal);
        private readonly List<string> _zoneOrder = new();
        public List<string> Warnings { get; } = new();

        public ReverseParseContext(SystemBuilder owner)
        {
            _owner = owner;
        }

        public Dictionary<string, object?> ParseSystem(Type sysType, object sys)
        {
            var displayName = sysType.GetProperty("DisplayName")?.GetValue(sys)?.ToString();
            var airLoopsOut = new List<Dictionary<string, object?>>();
            var plantLoopsOut = new List<Dictionary<string, object?>>();
            var vrfsOut = new List<Dictionary<string, object?>>();

            if (sysType.GetProperty("AirLoops")?.GetValue(sys) is IEnumerable airLoops)
            {
                foreach (var loop in airLoops)
                {
                    if (loop == null) continue;
                    var loopType = loop.GetType();
                    if (loopType.Name == "IB_NoAirLoop")
                    {
                        if (loopType.GetProperty("ThermalZones")?.GetValue(loop) is IEnumerable zones)
                        {
                            foreach (var z in zones)
                            {
                                if (z != null) RegisterThermalZone(z);
                            }
                        }
                        continue;
                    }
                    if (loopType.Name == "IB_ExistAirLoop")
                    {
                        Warnings.Add("IB_ExistAirLoop encountered during reverse_parse; inspect air_loops carefully before rebuilding.");
                        continue;
                    }
                    airLoopsOut.Add(ParseAirLoop(loopType, loop));
                }
            }

            if (sysType.GetProperty("PlantLoops")?.GetValue(sys) is IEnumerable plantLoops)
            {
                foreach (var loop in plantLoops)
                {
                    if (loop == null) continue;
                    var loopType = loop.GetType();
                    if (loopType.Name == "IB_ExistPlantLoop")
                    {
                        Warnings.Add("IB_ExistPlantLoop encountered during reverse_parse; inspect plant_loops carefully before rebuilding.");
                        continue;
                    }
                    plantLoopsOut.Add(ParsePlantLoop(loopType, loop));
                }
            }

            if (sysType.GetProperty("VariableRefrigerantFlows")?.GetValue(sys) is IEnumerable vrfs)
            {
                foreach (var vrf in vrfs)
                {
                    if (vrf == null) continue;
                    var vrfType = vrf.GetType();
                    var vrfId = RegisterComponent(vrf, skipProps: new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "Terminals" });
                    var terms = new List<string>();
                    if (vrfType.GetProperty("Terminals")?.GetValue(vrf) is IEnumerable termEnum)
                    {
                        foreach (var t in termEnum)
                        {
                            if (t != null) terms.Add(RegisterComponent(t));
                        }
                    }
                    vrfsOut.Add(new Dictionary<string, object?>
                    {
                        ["vrf"] = vrfId,
                        ["terminals"] = terms,
                    });
                }
            }

            var zonesOut = _zoneOrder.Select(rn => _zonesByRoom[rn]).ToList();
            return new Dictionary<string, object?>
            {
                ["schema_version"] = 1,
                ["display_name"] = displayName,
                ["imported_only"] = false,
                ["components"] = _components,
                ["thermal_zones"] = zonesOut,
                ["air_loops"] = airLoopsOut,
                ["plant_loops"] = plantLoopsOut,
                ["vrf_systems"] = vrfsOut,
                ["energy_management_system"] = null,
                ["electric_load_center"] = null,
            };
        }

        private Dictionary<string, object?> ParseAirLoop(Type loopType, object loop)
        {
            var entry = new Dictionary<string, object?>();
            var (name, fields, availMgrs) = ExtractLoopAttributes(loop);
            if (!string.IsNullOrWhiteSpace(name)) entry["name"] = name;
            if (fields.Count > 0) entry["fields"] = fields;
            if (availMgrs.Count > 0) entry["availability_managers"] = availMgrs;

            var sizingSys = loopType.GetProperty("SizingSystem")?.GetValue(loop);
            if (sizingSys != null)
            {
                entry["sizing_system"] = RegisterComponent(sizingSys);
            }

            var supplyIds = new List<string>();
            if (loopType.GetProperty("SupplyComponents")?.GetValue(loop) is IEnumerable supEnum)
            {
                foreach (var item in supEnum)
                {
                    if (item != null) supplyIds.Add(RegisterComponent(item));
                }
            }
            if (supplyIds.Count > 0) entry["supply"] = supplyIds;

            var demandBranches = new List<List<string>>();
            if (loopType.GetProperty("DemandComponents")?.GetValue(loop) is IEnumerable demEnum)
            {
                foreach (var item in demEnum)
                {
                    if (item == null) continue;
                    var branchesProp = item.GetType().GetProperty("Branches");
                    if (branchesProp?.GetValue(item) is IEnumerable branchesEnum)
                    {
                        foreach (var branch in branchesEnum)
                        {
                            if (branch is not IEnumerable branchItems) continue;
                            var branchRooms = new List<string>();
                            foreach (var z in branchItems)
                            {
                                if (z == null) continue;
                                if (z.GetType().Name == "IB_ThermalZone")
                                {
                                    branchRooms.Add(RegisterThermalZone(z));
                                }
                                else
                                {
                                    branchRooms.Add(RegisterComponent(z));
                                }
                            }
                            if (branchRooms.Count > 0) demandBranches.Add(branchRooms);
                        }
                    }
                    else if (item.GetType().Name == "IB_ThermalZone")
                    {
                        demandBranches.Add(new List<string> { RegisterThermalZone(item) });
                    }
                }
            }
            if (demandBranches.Count > 0)
            {
                if (demandBranches.All(b => b.Count == 1))
                    entry["demand_zones"] = demandBranches.Select(b => b[0]).ToList();
                else
                    entry["demand_branches"] = demandBranches;
            }

            AppendEmsAndOutputVars(loopType, loop, entry);
            return entry;
        }

        private Dictionary<string, object?> ParsePlantLoop(Type loopType, object loop)
        {
            var entry = new Dictionary<string, object?>();
            var (name, fields, availMgrs) = ExtractLoopAttributes(loop);
            if (!string.IsNullOrWhiteSpace(name)) entry["name"] = name;
            if (fields.Count > 0) entry["fields"] = fields;
            if (availMgrs.Count > 0) entry["availability_managers"] = availMgrs;

            var sizingPlant = loopType.GetProperty("SizingPlant")?.GetValue(loop);
            if (sizingPlant != null)
            {
                entry["sizing_plant"] = RegisterComponent(sizingPlant);
            }
            var opScheme = loopType.GetProperty("OperationScheme")?.GetValue(loop);
            if (opScheme != null)
            {
                entry["operation_scheme"] = RegisterComponent(opScheme);
            }

            if (loopType.GetProperty("SupplyComponents")?.GetValue(loop) is IEnumerable supEnum)
            {
                var supItems = supEnum.Cast<object?>().Where(x => x != null).ToList()!;
                var (serialItems, branchGroups, trailingSpm) = SplitPlantSide(supItems!);
                if (branchGroups.Count == 1 && serialItems.All(x => x is string))
                {
                    if (serialItems.Count > 0) entry["supply"] = serialItems;
                    entry["supply_branches"] = branchGroups[0];
                    if (trailingSpm != null) entry["supply_setpoint_manager"] = trailingSpm;
                }
                else
                {
                    var combined = new List<object>();
                    combined.AddRange(serialItems);
                    if (trailingSpm != null) combined.Add(trailingSpm);
                    if (combined.Count > 0) entry["supply"] = combined;
                }
            }

            if (loopType.GetProperty("DemandComponents")?.GetValue(loop) is IEnumerable demEnum)
            {
                var demItems = demEnum.Cast<object?>().Where(x => x != null).ToList()!;
                var (serialItems, branchGroups, _) = SplitPlantSide(demItems!, allowTrailingSpm: false);
                if (branchGroups.Count == 1 && serialItems.All(x => x is string))
                {
                    if (serialItems.Count > 0) entry["demand"] = serialItems;
                    entry["demand_branches"] = branchGroups[0];
                }
                else if (serialItems.Count > 0)
                {
                    entry["demand"] = serialItems;
                }
            }

            AppendEmsAndOutputVars(loopType, loop, entry);
            return entry;
        }

        private (List<object> SerialItems, List<List<List<string>>> BranchGroups, string? TrailingSpm) SplitPlantSide(
            List<object> rawItems,
            bool allowTrailingSpm = true)
        {
            var items = new List<object>(rawItems);
            string? trailingSpm = null;
            if (allowTrailingSpm && items.Count > 0)
            {
                var last = items[^1];
                var lastBase = last.GetType().BaseType?.Name ?? "";
                if (lastBase == "IB_SetpointManager" || last.GetType().Name.StartsWith("IB_SetpointManager", StringComparison.Ordinal))
                {
                    trailingSpm = RegisterComponent(last);
                    items.RemoveAt(items.Count - 1);
                }
            }

            var serial = new List<object>();
            var branchGroups = new List<List<List<string>>>();
            foreach (var item in items)
            {
                if (item.GetType().GetProperty("Branches")?.GetValue(item) is IEnumerable branchesEnum)
                {
                    var group = new List<List<string>>();
                    foreach (var b in branchesEnum)
                    {
                        if (b is not IEnumerable bEnum) continue;
                        var ids = new List<string>();
                        foreach (var c in bEnum)
                        {
                            if (c != null) ids.Add(RegisterComponent(c));
                        }
                        if (ids.Count > 0) group.Add(ids);
                    }
                    branchGroups.Add(group);
                    serial.Add(group);
                }
                else
                {
                    serial.Add(RegisterComponent(item));
                }
            }

            if (branchGroups.Count == 1 && serial.Count(x => x is List<List<string>>) == 1 && serial[^1] is List<List<string>>)
            {
                serial.RemoveAt(serial.Count - 1);
            }
            return (serial, branchGroups, trailingSpm);
        }

        private string RegisterThermalZone(object zoneObj)
        {
            var zt = zoneObj.GetType();
            var zoneName = zt.GetProperty("ZoneName")?.GetValue(zoneObj)?.ToString();
            var fields = ExtractFields(zt, zoneObj, out var tagComment);
            if (string.IsNullOrWhiteSpace(zoneName) && fields.TryGetValue("Name", out var nVal))
                zoneName = nVal?.ToString();
            zoneName = string.IsNullOrWhiteSpace(zoneName) ? $"Zone_{_zoneOrder.Count + 1}" : zoneName!;

            if (_zonesByRoom.ContainsKey(zoneName))
                return zoneName;

            fields.Remove("Name");
            var tzDict = new Dictionary<string, object?>
            {
                ["room_name"] = zoneName,
            };
            _zonesByRoom[zoneName] = tzDict;
            _zoneOrder.Add(zoneName);

            var sizingZone = zt.GetProperty("SizingZone")?.GetValue(zoneObj);
            if (sizingZone != null) tzDict["sizing_zone"] = RegisterComponent(sizingZone);

            var airTerm = zt.GetProperty("AirTerminal")?.GetValue(zoneObj);
            if (airTerm != null) tzDict["air_terminal"] = RegisterComponent(airTerm);

            if (zt.GetProperty("ZoneEquipments")?.GetValue(zoneObj) is IEnumerable eqEnum)
            {
                var eqIds = new List<string>();
                foreach (var eq in eqEnum)
                {
                    if (eq != null) eqIds.Add(RegisterComponent(eq));
                }
                if (eqIds.Count > 0) tzDict["zone_equipments"] = eqIds;
            }

            if (zt.GetProperty("AllowMultiAirLoops")?.GetValue(zoneObj) is bool ama && ama)
                tzDict["allow_multi_air_loops"] = true;
            if (zt.GetProperty("IsAirTerminalBeforeZoneEquipments")?.GetValue(zoneObj) is bool atb && atb)
                tzDict["is_air_terminal_before_zone_equipments"] = true;

            var supPlenum = zt.GetProperty("SupplyPlenum")?.GetValue(zoneObj);
            if (supPlenum != null)
            {
                var spName = supPlenum.GetType().GetProperty("ZoneName")?.GetValue(supPlenum)?.ToString();
                tzDict["supply_plenum"] = !string.IsNullOrWhiteSpace(spName) ? spName : RegisterComponent(supPlenum);
            }
            var retPlenum = zt.GetProperty("ReturnPlenum")?.GetValue(zoneObj);
            if (retPlenum != null)
            {
                var rpName = retPlenum.GetType().GetProperty("ZoneName")?.GetValue(retPlenum)?.ToString();
                tzDict["return_plenum"] = !string.IsNullOrWhiteSpace(rpName) ? rpName : RegisterComponent(retPlenum);
            }

            if (zt.GetProperty("IBProperties")?.GetValue(zoneObj) is IDictionary ibProps
                && ibProps.Contains("EquipmentListPriorities")
                && ibProps["EquipmentListPriorities"] is string epJson
                && !string.IsNullOrWhiteSpace(epJson))
            {
                try
                {
                    tzDict["equipment_list_priorities"] = JsonSerializer.Deserialize<object>(epJson);
                }
                catch
                {
                }
            }

            if (fields.Count > 0) tzDict["fields"] = fields;
            AppendEmsAndOutputVars(zt, zoneObj, tzDict);
            return zoneName;
        }

        private (string? Name, Dictionary<string, object?> Fields, List<string> AvailabilityManagers) ExtractLoopAttributes(object loopObj)
        {
            var lt = loopObj.GetType();
            var fields = ExtractFields(lt, loopObj, out _);
            string? name = null;
            if (fields.TryGetValue("Name", out var nVal))
            {
                name = nVal?.ToString();
                fields.Remove("Name");
            }
            var availMgrs = new List<string>();
            if (lt.GetProperty("CustomAttributes")?.GetValue(loopObj) is IEnumerable caEnum)
            {
                foreach (var arg in caEnum)
                {
                    if (arg == null) continue;
                    var fObj = arg.GetType().GetProperty("Field")?.GetValue(arg);
                    var fn = fObj?.GetType().GetProperty("FullName")?.GetValue(fObj)?.ToString();
                    if (!string.Equals(fn, "AvailabilityManagers", StringComparison.OrdinalIgnoreCase)) continue;
                    var val = arg.GetType().GetProperty("Value")?.GetValue(arg);
                    if (val != null && val.GetType().GetProperty("Mangers")?.GetValue(val) is IEnumerable mgrs)
                    {
                        foreach (var m in mgrs)
                        {
                            if (m != null) availMgrs.Add(RegisterComponent(m));
                        }
                    }
                    fields.Remove("AvailabilityManagers");
                }
            }
            return (name, fields, availMgrs);
        }

        private string RegisterComponent(object obj, HashSet<string>? skipProps = null)
        {
            if (_objToId.TryGetValue(obj, out var existingByRef))
                return existingByRef;

            var type = obj.GetType();
            var rawTag = type.GetMethod("GetTrackingTagID")?.Invoke(obj, null)?.ToString();
            if (!string.IsNullOrWhiteSpace(rawTag) && _trackingToId.TryGetValue(rawTag, out var existingByTid))
            {
                _objToId[obj] = existingByTid;
                return existingByTid;
            }

            var fields = ExtractFields(type, obj, out _);
            string baseSlug = CatalogInspector.ToSnakeCase(type.Name.StartsWith("IB_", StringComparison.Ordinal) ? type.Name[3..] : type.Name);
            if (fields.TryGetValue("Name", out var nameObj) && nameObj is string nameStr && !string.IsNullOrWhiteSpace(nameStr))
            {
                var cleaned = new string(nameStr.Trim().Select(c => char.IsLetterOrDigit(c) ? char.ToLowerInvariant(c) : '_').ToArray()).Trim('_');
                if (!string.IsNullOrWhiteSpace(cleaned))
                    baseSlug = cleaned;
            }

            int idx = _counters.GetValueOrDefault(baseSlug) + 1;
            _counters[baseSlug] = idx;
            var compId = idx == 1 && !_components.ContainsKey(baseSlug) ? baseSlug : $"{baseSlug}_{idx}";
            while (_components.ContainsKey(compId))
            {
                idx++;
                _counters[baseSlug] = idx;
                compId = $"{baseSlug}_{idx}";
            }

            _objToId[obj] = compId;
            if (!string.IsNullOrWhiteSpace(rawTag))
                _trackingToId[rawTag] = compId;

            var spec = new Dictionary<string, object?>
            {
                ["type"] = type.Name,
            };
            _components[compId] = spec;

            if (!string.IsNullOrWhiteSpace(rawTag))
                spec["tracking_id"] = rawTag;
            if (fields.Count > 0)
                spec["fields"] = fields;

            PopulateChildrenAndWiring(type, obj, spec, skipProps);
            AppendEmsAndOutputVars(type, obj, spec);
            return compId;
        }

        private void PopulateChildrenAndWiring(
            Type type,
            object obj,
            Dictionary<string, object?> spec,
            HashSet<string>? skipProps)
        {
            var children = new List<object>();
            if (type.GetProperty("Children")?.GetValue(obj) is IEnumerable chEnum)
            {
                foreach (var c in chEnum)
                {
                    if (c != null) children.Add(c);
                }
            }

            var ibPropsDict = new Dictionary<string, object?>();
            if (type.GetProperty("IBProperties")?.GetValue(obj) is IDictionary rawIbProps)
            {
                foreach (DictionaryEntry de in rawIbProps)
                {
                    var k = de.Key?.ToString();
                    if (string.IsNullOrWhiteSpace(k)) continue;
                    ibPropsDict[k] = de.Value;
                }
            }

            var ctorArgs = new List<object?>();
            var wiring = new Dictionary<string, object?>();
            var unmappedChildren = new List<string>();
            var unmappedIbProps = new Dictionary<string, object?>();

            // Special known constructors whose Children order differs from constructor order or relies on IBProperties
            bool handledSpecial = false;
            switch (type.Name)
            {
                case "IB_ZoneHVACPackagedTerminalAirConditioner" when children.Count >= 3:
                    ctorArgs.Add(RegisterComponent(children[2])); // Fan
                    ctorArgs.Add(RegisterComponent(children[1])); // HeatingCoil
                    ctorArgs.Add(RegisterComponent(children[0])); // CoolingCoil
                    handledSpecial = true;
                    break;
                case "IB_ZoneHVACPackagedTerminalHeatPump" when children.Count >= 4:
                case "IB_ZoneHVACWaterToAirHeatPump" when children.Count >= 4:
                    ctorArgs.Add(RegisterComponent(children[2])); // Fan
                    ctorArgs.Add(RegisterComponent(children[1])); // HeatingCoil
                    ctorArgs.Add(RegisterComponent(children[0])); // CoolingCoil
                    ctorArgs.Add(RegisterComponent(children[3])); // SupplementalHeatingCoil
                    handledSpecial = true;
                    break;
                case "IB_ZoneHVACEnergyRecoveryVentilator" when children.Count >= 3:
                case "IB_ZoneHVACLowTempRadiantVarFlow" when children.Count >= 2:
                case "IB_WaterUseEquipment" when children.Count >= 1:
                case "IB_CoilHeatingDesuperheater" when children.Count >= 1:
                case "IB_AirTerminalSingleDuctInletSideMixer" when children.Count >= 1:
                    foreach (var c in children) ctorArgs.Add(RegisterComponent(c));
                    handledSpecial = true;
                    break;
                case "IB_ZoneHVACLowTempRadiantConstFlow" when children.Count >= 2:
                    ctorArgs.Add(RegisterComponent(children[0]));
                    ctorArgs.Add(RegisterComponent(children[1]));
                    if (ibPropsDict.TryGetValue("TubingLength", out var tlVal))
                    {
                        ctorArgs.Add(ConvertSafeJsonValue(tlVal));
                        ibPropsDict.Remove("TubingLength");
                    }
                    else
                    {
                        ctorArgs.Add(0.0);
                    }
                    handledSpecial = true;
                    break;
                case "IB_CoilCoolingLowTempRadiantConstFlow":
                case "IB_CoilHeatingLowTempRadiantConstFlow":
                    foreach (var pk in new[] { "WaterHiT", "WaterLoT", "AirHiT", "AirLoT" })
                    {
                        ctorArgs.Add(ibPropsDict.TryGetValue(pk, out var pv) ? ConvertSafeJsonValue(pv) : 0.0);
                        ibPropsDict.Remove(pk);
                    }
                    handledSpecial = true;
                    break;
                case "IB_CoilCoolingLowTempRadiantVarFlow":
                    ctorArgs.Add(ibPropsDict.TryGetValue("AirHiT", out var aht) ? ConvertSafeJsonValue(aht) : 24.0);
                    ibPropsDict.Remove("AirHiT");
                    handledSpecial = true;
                    break;
                case "IB_CoilHeatingLowTempRadiantVarFlow":
                    ctorArgs.Add(ibPropsDict.TryGetValue("AirLoT", out var alt) ? ConvertSafeJsonValue(alt) : 21.0);
                    ibPropsDict.Remove("AirLoT");
                    handledSpecial = true;
                    break;
                case "IB_ScheduleDay":
                    if (ibPropsDict.TryGetValue("constantNumber", out var cnVal))
                    {
                        ctorArgs.Add(ConvertSafeJsonValue(cnVal));
                        ibPropsDict.Remove("constantNumber");
                        handledSpecial = true;
                    }
                    else if (ibPropsDict.TryGetValue("valuesFor24Hrs", out var v24Val))
                    {
                        ctorArgs.Add(ConvertSafeJsonValue(v24Val));
                        ibPropsDict.Remove("valuesFor24Hrs");
                        handledSpecial = true;
                    }
                    break;
                case "IB_ScheduleFile":
                    if (ibPropsDict.TryGetValue("filePath", out var fpVal))
                    {
                        ctorArgs.Add(ConvertSafeJsonValue(fpVal));
                        ibPropsDict.Remove("filePath");
                        handledSpecial = true;
                    }
                    break;
            }

            if (!handledSpecial && children.Count > 0)
            {
                // Check if type has a constructor matching children count and types (e.g., IB_ChillerElectricEIR(c1, c2, c3))
                var setMethods = type.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                    .Where(m => !m.IsSpecialName
                        && m.Name.StartsWith("Set", StringComparison.Ordinal)
                        && m.DeclaringType != typeof(object)
                        && m.DeclaringType?.Name is not ("IB_ModelObject" or "IB_HVACObject")
                        && m.GetParameters().Length == 1)
                    .ToList();

                var matchingCtor = type.GetConstructors(BindingFlags.Public | BindingFlags.Instance)
                    .FirstOrDefault(c =>
                    {
                        var ps = c.GetParameters();
                        return ps.Length == children.Count
                            && ps.Select((p, i) => p.ParameterType.IsInstanceOfType(children[i])).All(ok => ok);
                    });

                // Prefer Set* wiring when every child uniquely maps to a Set* slot and type has parameterless ctor
                bool hasDefaultCtor = type.GetConstructor(Type.EmptyTypes) != null
                    || type.GetConstructors().Any(c => c.GetParameters().All(p => p.HasDefaultValue));

                var matchedSetSlots = new List<(string Slot, string ChildId)>();
                var usedMethods = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                bool allMatchedBySet = hasDefaultCtor;
                if (allMatchedBySet)
                {
                    foreach (var child in children)
                    {
                        var matches = setMethods
                            .Where(m => !usedMethods.Contains(m.Name) && m.GetParameters()[0].ParameterType.IsInstanceOfType(child))
                            .ToList();
                        if (matches.Count == 1)
                        {
                            usedMethods.Add(matches[0].Name);
                            matchedSetSlots.Add((CatalogInspector.ToSnakeCase(matches[0].Name[3..]), RegisterComponent(child)));
                        }
                        else
                        {
                            allMatchedBySet = false;
                            break;
                        }
                    }
                }

                if (allMatchedBySet && matchedSetSlots.Count == children.Count)
                {
                    foreach (var (slot, cid) in matchedSetSlots)
                        wiring[slot] = cid;
                }
                else if (matchingCtor != null)
                {
                    foreach (var child in children)
                        ctorArgs.Add(RegisterComponent(child));
                }
                else
                {
                    foreach (var child in children)
                        unmappedChildren.Add(RegisterComponent(child));
                }
            }

            // Map IBProperties (such as OAStreamObjs / ReliefStreamObjs) to wiring when matching property exists
            foreach (var kv in ibPropsDict)
            {
                if (skipProps != null && skipProps.Contains(kv.Key)) continue;
                var prop = type.GetProperty(kv.Key, BindingFlags.Public | BindingFlags.Instance);
                if (prop != null && (prop.CanWrite || typeof(IList).IsAssignableFrom(prop.PropertyType)))
                {
                    wiring[CatalogInspector.ToSnakeCase(kv.Key)] = ConvertSafeJsonValue(kv.Value);
                }
                else
                {
                    unmappedIbProps[kv.Key] = ConvertSafeJsonValue(kv.Value);
                }
            }

            // Also inspect declared IB_ModelObject properties not already captured in Children/IBProperties
            foreach (var prop in type.GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly))
            {
                if (skipProps != null && skipProps.Contains(prop.Name)) continue;
                if (!prop.CanRead || !prop.CanWrite) continue;
                if (prop.Name is "Memo" or "Children" or "CustomAttributes" or "IBProperties") continue;
                var val = prop.GetValue(obj);
                if (val == null) continue;
                var ibModelType = _owner._runtime.ResolveHvacType("IB_ModelObject");
                if (ibModelType.IsInstanceOfType(val))
                {
                    var childId = RegisterComponent(val);
                    var slot = CatalogInspector.ToSnakeCase(prop.Name);
                    if (!wiring.ContainsKey(slot) && !unmappedChildren.Contains(childId) && !ctorArgs.Contains(childId))
                    {
                        wiring[slot] = childId;
                    }
                }
            }

            if (ctorArgs.Count > 0) spec["ctor_args"] = ctorArgs;
            if (wiring.Count > 0) spec["wiring"] = wiring;
            if (unmappedChildren.Count > 0) spec["children"] = unmappedChildren;
            if (unmappedIbProps.Count > 0) spec["ib_properties"] = unmappedIbProps;
        }

        private Dictionary<string, object?> ExtractFields(Type type, object obj, out string? trackingComment)
        {
            trackingComment = null;
            var fields = new Dictionary<string, object?>(StringComparer.Ordinal);
            var caObj = type.GetProperty("CustomAttributes")?.GetValue(obj);
            if (caObj is not IEnumerable caEnum) return fields;

            var rawTag = type.GetMethod("GetTrackingTagID")?.Invoke(obj, null)?.ToString();
            foreach (var arg in caEnum)
            {
                if (arg == null) continue;
                var fObj = arg.GetType().GetProperty("Field")?.GetValue(arg);
                var fn = fObj?.GetType().GetProperty("FullName")?.GetValue(fObj)?.ToString();
                if (string.IsNullOrWhiteSpace(fn)) continue;
                var val = arg.GetType().GetProperty("Value")?.GetValue(arg);
                if (string.Equals(fn, "Comment", StringComparison.OrdinalIgnoreCase) && val is string sVal)
                {
                    if (sVal == rawTag || sVal.StartsWith("TrackingID:", StringComparison.OrdinalIgnoreCase) || sVal.StartsWith("! TrackingID:", StringComparison.OrdinalIgnoreCase))
                    {
                        trackingComment = sVal;
                        continue;
                    }
                }
                if (string.Equals(fn, "AvailabilityManagers", StringComparison.OrdinalIgnoreCase))
                    continue;

                fields[fn] = ConvertSafeJsonValue(val);
            }
            return fields;
        }

        private void AppendEmsAndOutputVars(Type type, object obj, Dictionary<string, object?> target)
        {
            if (type.GetProperty("CustomOutputVariables")?.GetValue(obj) is IEnumerable ovEnum)
            {
                var ovs = new List<Dictionary<string, object?>>();
                foreach (var ov in ovEnum)
                {
                    if (ov == null) continue;
                    var varName = ov.GetType().GetProperty("VariableName")?.GetValue(ov)?.ToString();
                    var ts = ov.GetType().GetProperty("TimeStep")?.GetValue(ov)?.ToString() ?? "Hourly";
                    if (!string.IsNullOrWhiteSpace(varName))
                    {
                        ovs.Add(new Dictionary<string, object?>
                        {
                            ["variable_name"] = varName,
                            ["reporting_frequency"] = ts,
                        });
                    }
                }
                if (ovs.Count > 0) target["output_variables"] = ovs;
            }

            if (type.GetProperty("CustomSensors")?.GetValue(obj) is IEnumerable sEnum)
            {
                var sensors = new List<Dictionary<string, object?>>();
                foreach (var s in sEnum)
                {
                    if (s == null) continue;
                    var st = s.GetType();
                    var sFields = ExtractFields(st, s, out _);
                    var item = new Dictionary<string, object?>();
                    var rawTag = st.GetMethod("GetTrackingTagID")?.Invoke(s, null)?.ToString();
                    if (!string.IsNullOrWhiteSpace(rawTag)) item["tracking_id"] = rawTag;
                    if (sFields.TryGetValue("Name", out var nVal) && nVal != null) { item["name"] = nVal; sFields.Remove("Name"); }
                    if (sFields.TryGetValue("KeyName", out var kVal) && kVal != null) { item["key_name"] = kVal; sFields.Remove("KeyName"); }
                    if (sFields.TryGetValue("OutputVariableOrMeterName", out var oVal) && oVal != null) { item["output_variable"] = oVal; sFields.Remove("OutputVariableOrMeterName"); }
                    if (sFields.Count > 0) item["fields"] = sFields;
                    sensors.Add(item);
                }
                if (sensors.Count > 0) target["ems_sensors"] = sensors;
            }

            if (type.GetProperty("CustomInternalVariables")?.GetValue(obj) is IEnumerable ivEnum)
            {
                var ivs = new List<Dictionary<string, object?>>();
                foreach (var iv in ivEnum)
                {
                    if (iv == null) continue;
                    var ivt = iv.GetType();
                    var ivFields = ExtractFields(ivt, iv, out _);
                    var item = new Dictionary<string, object?>();
                    var rawTag = ivt.GetMethod("GetTrackingTagID")?.Invoke(iv, null)?.ToString();
                    if (!string.IsNullOrWhiteSpace(rawTag)) item["tracking_id"] = rawTag;
                    if (ivFields.TryGetValue("Name", out var nVal) && nVal != null) { item["name"] = nVal; ivFields.Remove("Name"); }
                    if (ivFields.TryGetValue("InternalDataType", out var dtVal) && dtVal != null) { item["internal_data_type"] = dtVal; ivFields.Remove("InternalDataType"); }
                    var hostObj = ivt.GetProperty("HostObj")?.GetValue(iv);
                    if (hostObj != null) item["host_obj"] = RegisterComponent(hostObj);
                    if (ivFields.Count > 0) item["fields"] = ivFields;
                    ivs.Add(item);
                }
                if (ivs.Count > 0) target["ems_internal_variables"] = ivs;
            }

            if (type.GetProperty("CustomActuators")?.GetValue(obj) is IEnumerable aEnum)
            {
                var acts = new List<Dictionary<string, object?>>();
                foreach (var a in aEnum)
                {
                    if (a == null) continue;
                    var at = a.GetType();
                    var aFields = ExtractFields(at, a, out _);
                    var item = new Dictionary<string, object?>();
                    var rawTag = at.GetMethod("GetTrackingTagID")?.Invoke(a, null)?.ToString();
                    if (!string.IsNullOrWhiteSpace(rawTag)) item["tracking_id"] = rawTag;
                    if (aFields.TryGetValue("Name", out var nVal) && nVal != null) { item["name"] = nVal; aFields.Remove("Name"); }
                    if (aFields.TryGetValue("ActuatedComponentType", out var ctVal) && ctVal != null) { item["actuated_component_type"] = ctVal; aFields.Remove("ActuatedComponentType"); }
                    if (aFields.TryGetValue("ActuatedComponentControlType", out var ccVal) && ccVal != null) { item["actuated_component_control_type"] = ccVal; aFields.Remove("ActuatedComponentControlType"); }
                    if (aFields.Count > 0) item["fields"] = aFields;
                    acts.Add(item);
                }
                if (acts.Count > 0) target["ems_actuators"] = acts;
            }
        }

        private object? ConvertSafeJsonValue(object? val)
        {
            if (val == null) return null;
            var ibModelType = _owner._runtime.ResolveHvacType("IB_ModelObject");
            if (ibModelType.IsInstanceOfType(val))
            {
                return "@" + RegisterComponent(val);
            }
            if (val is double d)
                return double.IsFinite(d) ? d : null;
            if (val is float f)
                return float.IsFinite(f) ? (double)f : null;
            if (val is bool or int or long or string)
                return val;
            if (val.GetType().IsEnum)
                return val.ToString();
            if (val is IEnumerable en and not string)
            {
                var list = new List<object?>();
                foreach (var item in en)
                {
                    var converted = ConvertSafeJsonValue(item);
                    if (converted is string s && s.StartsWith("@", StringComparison.Ordinal))
                        list.Add(s[1..]);
                    else
                        list.Add(converted);
                }
                return list;
            }
            return val.ToString();
        }
    }

    private void ApplyZoneEquipmentPriorities(
        Type sysType,
        object sys,
        Assembly osAsm,
        Type osModelType,
        object osModel,
        List<string> warnings)
    {
        var airLoops = sysType.GetProperty("AirLoops")?.GetValue(sys) as IEnumerable;
        if (airLoops == null) return;

        var ibZones = new List<object>();
        foreach (var loop in airLoops)
        {
            if (loop == null) continue;
            if (loop.GetType().Name == "IB_NoAirLoop")
            {
                if (loop.GetType().GetProperty("ThermalZones")?.GetValue(loop) is IEnumerable tzs)
                {
                    foreach (var z in tzs) if (z != null) ibZones.Add(z);
                }
            }
            else if (loop.GetType().GetProperty("DemandComponents")?.GetValue(loop) is IEnumerable dem)
            {
                foreach (var d in dem)
                {
                    if (d?.GetType().GetProperty("Branches")?.GetValue(d) is IEnumerable branches)
                    {
                        foreach (var br in branches)
                        {
                            if (br is not IEnumerable bEnum) continue;
                            foreach (var z in bEnum)
                            {
                                if (z != null && z.GetType().Name == "IB_ThermalZone") ibZones.Add(z);
                            }
                        }
                    }
                }
            }
        }
        if (ibZones.Count == 0) return;

        var osModelObjType = osAsm.GetType("OpenStudio.ModelObject");
        var osZoneVec = osModelType.GetMethod("getThermalZones", Type.EmptyTypes)?.Invoke(osModel, null) as IEnumerable;
        if (osZoneVec == null || osModelObjType == null) return;

        var osZonesByName = new Dictionary<string, object>(StringComparer.Ordinal);
        foreach (var oz in osZoneVec)
        {
            if (oz == null) continue;
            var zn = oz.GetType().GetMethod("nameString", Type.EmptyTypes)?.Invoke(oz, null)?.ToString();
            if (!string.IsNullOrWhiteSpace(zn)) osZonesByName[zn] = oz;
        }

        foreach (var ibZone in ibZones)
        {
            var zt = ibZone.GetType();
            if (zt.GetProperty("IBProperties")?.GetValue(ibZone) is not IDictionary ibProps) continue;
            if (!ibProps.Contains("EquipmentListPriorities")) continue;
            if (ibProps["EquipmentListPriorities"] is not string jsonStr || string.IsNullOrWhiteSpace(jsonStr)) continue;

            var zoneName = zt.GetProperty("ZoneName")?.GetValue(ibZone)?.ToString();
            if (string.IsNullOrWhiteSpace(zoneName) || !osZonesByName.TryGetValue(zoneName, out var osZone))
                continue;

            var eqCandidates = new List<object>();
            var at = zt.GetProperty("AirTerminal")?.GetValue(ibZone);
            if (at != null) eqCandidates.Add(at);
            if (zt.GetProperty("ZoneEquipments")?.GetValue(ibZone) is IEnumerable zeq)
            {
                foreach (var e in zeq) if (e != null) eqCandidates.Add(e);
            }

            var eqByTag = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);
            foreach (var eq in eqCandidates)
            {
                var tag = eq.GetType().GetMethod("GetTrackingTagID")?.Invoke(eq, null)?.ToString();
                if (!string.IsNullOrWhiteSpace(tag)) eqByTag[tag] = eq;
            }

            try
            {
                using var doc = JsonDocument.Parse(jsonStr);
                if (doc.RootElement.ValueKind != JsonValueKind.Array) continue;
                var setCool = osZone.GetType().GetMethod("setCoolingPriority", new[] { osModelObjType, typeof(uint) });
                var setHeat = osZone.GetType().GetMethod("setHeatingPriority", new[] { osModelObjType, typeof(uint) });

                foreach (var entry in doc.RootElement.EnumerateArray())
                {
                    var tag = entry.TryGetProperty("tracking_tag", out var tEl) && tEl.ValueKind == JsonValueKind.String
                        ? tEl.GetString()
                        : null;
                    if (string.IsNullOrWhiteSpace(tag) || !eqByTag.TryGetValue(tag, out var ibEq)) continue;
                    var osEq = ibEq.GetType().GetMethod("GetOsmObjInModel")?.Invoke(ibEq, new[] { osModel });
                    if (osEq == null) continue;
                    if (entry.TryGetProperty("cooling_priority", out var cEl) && cEl.ValueKind == JsonValueKind.Number)
                    {
                        setCool?.Invoke(osZone, new[] { osEq, (uint)Math.Max(1, cEl.GetInt32()) });
                    }
                    if (entry.TryGetProperty("heating_priority", out var hEl) && hEl.ValueKind == JsonValueKind.Number)
                    {
                        setHeat?.Invoke(osZone, new[] { osEq, (uint)Math.Max(1, hEl.GetInt32()) });
                    }
                }
            }
            catch (Exception ex)
            {
                warnings.Add($"Failed to apply equipment_list_priorities on zone '{zoneName}': {ex.Message}");
            }
        }
    }

    private static string? GetOpenStudioRuntimeVersion(Assembly osAsm)
    {
        try
        {
            var osUtilCore = osAsm.GetType("OpenStudio.OpenStudioUtilitiesCore");
            var ver = osUtilCore?.GetMethod("openStudioVersion", Type.EmptyTypes)?.Invoke(null, null)?.ToString()?.Trim();
            if (!string.IsNullOrWhiteSpace(ver))
                return ver;
        }
        catch
        {
        }
        return osAsm.GetName().Version?.ToString();
    }

    private static string? ExtractOsmVersionFromFile(string osmPath)
    {
        try
        {
            // OS:Version normally appears near the top of the file; inspect up to first 16 KB first.
            using var reader = new StreamReader(osmPath);
            var buf = new char[16384];
            int read = reader.Read(buf, 0, buf.Length);
            var head = new string(buf, 0, read);
            var match = Regex.Match(head, @"OS:Version\s*,[^;]*?(\d+\.\d+\.\d+(?:\.\d+)?)\s*;", RegexOptions.IgnoreCase | RegexOptions.Singleline);
            if (match.Success)
                return match.Groups[1].Value;
        }
        catch
        {
        }
        return null;
    }

    private static object? CreateOpenStudioWarnLogSink(Assembly osAsm)
    {
        try
        {
            var sinkType = osAsm.GetType("OpenStudio.StringStreamLogSink");
            if (sinkType == null) return null;
            var sink = Activator.CreateInstance(sinkType);
            if (sink == null) return null;
            var logLevelType = osAsm.GetType("OpenStudio.LogLevel");
            if (logLevelType != null && Enum.TryParse(logLevelType, "Warn", ignoreCase: true, out var warnLevel))
            {
                sinkType.GetMethod("setLogLevel", new[] { logLevelType })?.Invoke(sink, new[] { warnLevel });
            }
            return sink;
        }
        catch
        {
            return null;
        }
    }

    private static void DisposeOpenStudioLogSink(object? sink)
    {
        if (sink == null) return;
        try
        {
            sink.GetType().GetMethod("disable", Type.EmptyTypes)?.Invoke(sink, null);
        }
        catch
        {
        }
        (sink as IDisposable)?.Dispose();
    }

    private static void CollectLogMessageVector(
        object? msgVec,
        List<string> warnDest,
        List<string> errorDest,
        HashSet<string> seenWarn,
        HashSet<string> seenError)
    {
        if (msgVec is not IEnumerable msgs) return;
        foreach (var log in msgs)
        {
            if (log == null) continue;
            var lt = log.GetType();
            var rawMsg = lt.GetMethod("logMessage", Type.EmptyTypes)?.Invoke(log, null)?.ToString()?.Trim();
            if (string.IsNullOrWhiteSpace(rawMsg)) continue;
            var channel = lt.GetMethod("logChannel", Type.EmptyTypes)?.Invoke(log, null)?.ToString()?.Trim();
            var levelStr = lt.GetMethod("logLevel", Type.EmptyTypes)?.Invoke(log, null)?.ToString()?.Trim() ?? "";
            var formatted = string.IsNullOrWhiteSpace(channel) ? rawMsg : $"[{channel}] {rawMsg}";

            bool isErrorLevel = string.Equals(levelStr, "Error", StringComparison.OrdinalIgnoreCase)
                || string.Equals(levelStr, "Fatal", StringComparison.OrdinalIgnoreCase);
            if (isErrorLevel)
            {
                if (seenError.Add(formatted)) errorDest.Add(formatted);
            }
            else
            {
                if (seenWarn.Add(formatted)) warnDest.Add(formatted);
            }
        }
    }

    private static object LoadOsmModelWithDiagnostics(
        Assembly osAsm,
        Type osModelType,
        string fullOsmPath,
        ref string? osmVersion,
        List<string> errors,
        List<string> warnings,
        List<string> vtWarnings,
        List<string> vtErrors)
    {
        var osUtilCore = osAsm.GetType("OpenStudio.OpenStudioUtilitiesCore")
            ?? throw new TypeLoadException("OpenStudio.OpenStudioUtilitiesCore type not found.");
        var toPathMethod = osUtilCore.GetMethod("toPath", new[] { typeof(string) })
            ?? throw new MissingMethodException("OpenStudioUtilitiesCore.toPath(string) not found.");
        var osPath = toPathMethod.Invoke(null, new object[] { fullOsmPath })!;
        object? sink = CreateOpenStudioWarnLogSink(osAsm);

        var seenWarn = new HashSet<string>(StringComparer.Ordinal);
        var seenError = new HashSet<string>(StringComparer.Ordinal);

        try
        {
            var vtType = osAsm.GetType("OpenStudio.VersionTranslator");
            object? optModel = null;
            if (vtType != null)
            {
                var vt = Activator.CreateInstance(vtType)!;
                try
                {
                    vtType.GetMethod("setAllowNewerVersions", new[] { typeof(bool) })?.Invoke(vt, new object[] { true });
                    var vtLoad = vtType.GetMethod("loadModel", new[] { osPath.GetType() });
                    if (vtLoad != null)
                    {
                        optModel = vtLoad.Invoke(vt, new[] { osPath });
                        var origVerObj = vtType.GetMethod("originalVersion", Type.EmptyTypes)?.Invoke(vt, null);
                        var origVerStr = origVerObj?.GetType().GetMethod("str", Type.EmptyTypes)?.Invoke(origVerObj, null)?.ToString()?.Trim();
                        if (!string.IsNullOrWhiteSpace(origVerStr))
                        {
                            osmVersion = origVerStr;
                        }
                        CollectLogMessageVector(
                            vtType.GetMethod("warnings", Type.EmptyTypes)?.Invoke(vt, null),
                            vtWarnings,
                            vtErrors,
                            seenWarn,
                            seenError);
                        CollectLogMessageVector(
                            vtType.GetMethod("errors", Type.EmptyTypes)?.Invoke(vt, null),
                            vtErrors,
                            vtErrors,
                            seenError,
                            seenError);
                    }
                }
                finally
                {
                    (vt as IDisposable)?.Dispose();
                }
            }

            if (optModel == null)
            {
                var loadMethod = osModelType.GetMethod("load", new[] { osPath.GetType() })
                    ?? throw new MissingMethodException("OpenStudio.Model.load(OpenStudio.Path) not found.");
                optModel = loadMethod.Invoke(null, new[] { osPath })!;
            }

            if (sink != null)
            {
                CollectLogMessageVector(
                    sink.GetType().GetMethod("logMessages", Type.EmptyTypes)?.Invoke(sink, null),
                    vtWarnings,
                    vtErrors,
                    seenWarn,
                    seenError);
            }

            try
            {
                var isInit = optModel.GetType().GetMethod("is_initialized")?.Invoke(optModel, null) is bool init && init;
                if (!isInit)
                {
                    errors.Add($"Failed to load OpenStudio model from '{fullOsmPath}'.");
                    foreach (var vErr in vtErrors) errors.Add(vErr);
                    foreach (var vWarn in vtWarnings) warnings.Add(vWarn);
                    return Activator.CreateInstance(osModelType)!;
                }

                foreach (var vWarn in vtWarnings) warnings.Add(vWarn);
                foreach (var vErr in vtErrors) warnings.Add($"[OSM Load Error] {vErr}");
                return optModel.GetType().GetMethod("get")!.Invoke(optModel, null)!;
            }
            finally
            {
                (optModel as IDisposable)?.Dispose();
            }
        }
        finally
        {
            DisposeOpenStudioLogSink(sink);
            (osPath as IDisposable)?.Dispose();
        }
    }

    private static Dictionary<string, object?> RunForwardTranslatorCheck(
        Assembly osAsm,
        Type osModelType,
        object osModel,
        List<string> errors,
        List<string> warnings,
        List<string>? vtWarnings = null,
        List<string>? vtErrors = null,
        string? osmVersion = null,
        string? osRuntimeVersion = null)
    {
        var ftType = osAsm.GetType("OpenStudio.EnergyPlusForwardTranslator");
        if (ftType == null)
        {
            return new Dictionary<string, object?>
            {
                ["ran"] = false,
                ["reason"] = "OpenStudio.EnergyPlusForwardTranslator type not found.",
            };
        }

        var ftErrors = new List<string>();
        var ftWarnings = new List<string>();
        try
        {
            var ft = Activator.CreateInstance(ftType)!;
            ftType.GetMethod("translateModel", new[] { osModelType })?.Invoke(ft, new[] { osModel });

            void CollectLogs(string methodName, List<string> dest, List<string> agg)
            {
                if (ftType.GetMethod(methodName, Type.EmptyTypes)?.Invoke(ft, null) is IEnumerable logs)
                {
                    foreach (var log in logs)
                    {
                        var msg = log?.GetType().GetMethod("logMessage", Type.EmptyTypes)?.Invoke(log, null)?.ToString()?.Trim();
                        if (!string.IsNullOrEmpty(msg))
                        {
                            dest.Add(msg);
                            agg.Add($"[ForwardTranslator] {msg}");
                        }
                    }
                }
            }

            CollectLogs("errors", ftErrors, errors);
            CollectLogs("warnings", ftWarnings, warnings);
        }
        catch (Exception ex)
        {
            var inner = ex is TargetInvocationException tie && tie.InnerException != null ? tie.InnerException : ex;
            ftErrors.Add(inner.Message);
            errors.Add($"[ForwardTranslator] {inner.Message}");
        }

        var combinedWarnings = new List<string>(ftWarnings);
        if (vtWarnings != null)
        {
            foreach (var w in vtWarnings)
            {
                if (!combinedWarnings.Contains(w)) combinedWarnings.Add(w);
            }
        }
        if (vtErrors != null)
        {
            foreach (var e in vtErrors)
            {
                var tagged = $"[VersionTranslator/OSM] {e}";
                if (!combinedWarnings.Contains(tagged)) combinedWarnings.Add(tagged);
            }
        }

        var ftPayload = new Dictionary<string, object?>
        {
            ["ran"] = true,
            ["error_count"] = ftErrors.Count,
            ["warning_count"] = combinedWarnings.Count,
            ["errors"] = ftErrors,
            ["warnings"] = combinedWarnings,
        };
        if (!string.IsNullOrWhiteSpace(osmVersion))
            ftPayload["osm_version"] = osmVersion;
        if (!string.IsNullOrWhiteSpace(osRuntimeVersion))
            ftPayload["openstudio_version"] = osRuntimeVersion;
        if (vtWarnings != null && vtWarnings.Count > 0)
            ftPayload["version_translator_warnings"] = vtWarnings;
        if (vtErrors != null && vtErrors.Count > 0)
            ftPayload["version_translator_errors"] = vtErrors;
        return ftPayload;
    }

    private static Dictionary<string, int> BuildOpenStudioSummary(Type osModelType, object osModel)
    {
        int SumGetters(params string[] getters) => getters.Sum(g => CountOsObjects(osModelType, osModel, g));

        return new Dictionary<string, int>
        {
            // Core & existing keys (preserved verbatim)
            ["thermal_zones"] = CountOsObjects(osModelType, osModel, "getThermalZones"),
            ["air_loops"] = CountOsObjects(osModelType, osModel, "getAirLoopHVACs"),
            ["plant_loops"] = CountOsObjects(osModelType, osModel, "getPlantLoops"),
            ["vrf_systems"] = CountOsObjects(osModelType, osModel, "getAirConditionerVariableRefrigerantFlows"),
            ["zone_hvac_four_pipe_fan_coils"] = CountOsObjects(osModelType, osModel, "getZoneHVACFourPipeFanCoils"),
            ["zone_hvac_ptacs"] = CountOsObjects(osModelType, osModel, "getZoneHVACPackagedTerminalAirConditioners"),
            ["zone_hvac_pthps"] = CountOsObjects(osModelType, osModel, "getZoneHVACPackagedTerminalHeatPumps"),
            ["chillers_electric_eir"] = CountOsObjects(osModelType, osModel, "getChillerElectricEIRs"),
            ["boilers_hot_water"] = CountOsObjects(osModelType, osModel, "getBoilerHotWaters"),
            ["cooling_towers_variable_speed"] = CountOsObjects(osModelType, osModel, "getCoolingTowerVariableSpeeds"),
            ["coil_cooling_waters"] = CountOsObjects(osModelType, osModel, "getCoilCoolingWaters"),
            ["coil_heating_waters"] = CountOsObjects(osModelType, osModel, "getCoilHeatingWaters"),
            ["air_terminals_vav_reheat"] = CountOsObjects(osModelType, osModel, "getAirTerminalSingleDuctVAVReheats"),
            ["pumps_constant_speed"] = CountOsObjects(osModelType, osModel, "getPumpConstantSpeeds"),
            ["pumps_variable_speed"] = CountOsObjects(osModelType, osModel, "getPumpVariableSpeeds"),
            ["fans_on_off"] = CountOsObjects(osModelType, osModel, "getFanOnOffs"),
            ["fans_constant_volume"] = CountOsObjects(osModelType, osModel, "getFanConstantVolumes"),
            ["fans_variable_volume"] = CountOsObjects(osModelType, osModel, "getFanVariableVolumes"),

            // Expanded AirLoop / terminal / unitary / OA / heat recovery / plenum counts
            ["air_terminals_cv_no_reheat"] = CountOsObjects(osModelType, osModel, "getAirTerminalSingleDuctConstantVolumeNoReheats"),
            ["air_terminals_vav_no_reheat"] = CountOsObjects(osModelType, osModel, "getAirTerminalSingleDuctVAVNoReheats"),
            ["air_terminals_piu_parallel"] = CountOsObjects(osModelType, osModel, "getAirTerminalSingleDuctParallelPIUReheats"),
            ["air_terminals_piu_series"] = CountOsObjects(osModelType, osModel, "getAirTerminalSingleDuctSeriesPIUReheats"),
            ["air_terminals_chilled_beam"] = CountOsObjects(osModelType, osModel, "getAirTerminalSingleDuctConstantVolumeCooledBeams"),
            ["air_terminals_four_pipe_beam"] = CountOsObjects(osModelType, osModel, "getAirTerminalSingleDuctConstantVolumeFourPipeBeams"),
            ["outdoor_air_systems"] = CountOsObjects(osModelType, osModel, "getAirLoopHVACOutdoorAirSystems"),
            ["dedicated_outdoor_air_systems"] = CountOsObjects(osModelType, osModel, "getAirLoopHVACDedicatedOutdoorAirSystems"),
            ["unitary_systems"] = CountOsObjects(osModelType, osModel, "getAirLoopHVACUnitarySystems"),
            ["unitary_heat_pumps_air_to_air"] = SumGetters("getAirLoopHVACUnitaryHeatPumpAirToAirs", "getAirLoopHVACUnitaryHeatPumpAirToAirMultiSpeeds"),
            ["heat_exchangers_air_to_air"] = CountOsObjects(osModelType, osModel, "getHeatExchangerAirToAirSensibleAndLatents"),
            ["humidifiers_steam_electric"] = SumGetters("getHumidifierSteamElectrics", "getHumidifierSteamGass"),
            ["evaporative_coolers"] = SumGetters("getEvaporativeCoolerDirectResearchSpecials", "getEvaporativeCoolerIndirectResearchSpecials"),
            ["supply_plenums"] = CountOsObjects(osModelType, osModel, "getAirLoopHVACSupplyPlenums"),
            ["return_plenums"] = CountOsObjects(osModelType, osModel, "getAirLoopHVACReturnPlenums"),

            // Expanded Fan & Coil counts
            ["fans_system_model"] = CountOsObjects(osModelType, osModel, "getFanSystemModels"),
            ["fans_zone_exhaust"] = CountOsObjects(osModelType, osModel, "getFanZoneExhausts"),
            ["coil_cooling_dx_single_speed"] = CountOsObjects(osModelType, osModel, "getCoilCoolingDXSingleSpeeds"),
            ["coil_cooling_dx_two_speed"] = CountOsObjects(osModelType, osModel, "getCoilCoolingDXTwoSpeeds"),
            ["coil_cooling_dx_variable_speed"] = CountOsObjects(osModelType, osModel, "getCoilCoolingDXVariableSpeeds"),
            ["coil_cooling_dx_vrf"] = CountOsObjects(osModelType, osModel, "getCoilCoolingDXVariableRefrigerantFlows"),
            ["coil_cooling_water_to_air_hp"] = CountOsObjects(osModelType, osModel, "getCoilCoolingWaterToAirHeatPumpEquationFits"),
            ["coil_heating_electric"] = CountOsObjects(osModelType, osModel, "getCoilHeatingElectrics"),
            ["coil_heating_gas"] = CountOsObjects(osModelType, osModel, "getCoilHeatingGass"),
            ["coil_heating_dx_single_speed"] = CountOsObjects(osModelType, osModel, "getCoilHeatingDXSingleSpeeds"),
            ["coil_heating_dx_vrf"] = CountOsObjects(osModelType, osModel, "getCoilHeatingDXVariableRefrigerantFlows"),
            ["coil_heating_water_to_air_hp"] = CountOsObjects(osModelType, osModel, "getCoilHeatingWaterToAirHeatPumpEquationFits"),

            // Expanded Zone HVAC counts
            ["zone_hvac_vrf_terminals"] = CountOsObjects(osModelType, osModel, "getZoneHVACTerminalUnitVariableRefrigerantFlows"),
            ["zone_hvac_water_to_air_hps"] = CountOsObjects(osModelType, osModel, "getZoneHVACWaterToAirHeatPumps"),
            ["zone_hvac_unit_heaters"] = CountOsObjects(osModelType, osModel, "getZoneHVACUnitHeaters"),
            ["zone_hvac_unit_ventilators"] = CountOsObjects(osModelType, osModel, "getZoneHVACUnitVentilators"),
            ["zone_hvac_baseboards_water"] = CountOsObjects(osModelType, osModel, "getZoneHVACBaseboardConvectiveWaters"),
            ["zone_hvac_baseboards_electric"] = CountOsObjects(osModelType, osModel, "getZoneHVACBaseboardConvectiveElectrics"),
            ["zone_hvac_low_temp_radiant_var_flow"] = CountOsObjects(osModelType, osModel, "getZoneHVACLowTempRadiantVarFlows"),
            ["zone_hvac_low_temp_radiant_const_flow"] = CountOsObjects(osModelType, osModel, "getZoneHVACLowTempRadiantConstFlows"),
            ["zone_hvac_ervs"] = CountOsObjects(osModelType, osModel, "getZoneHVACEnergyRecoveryVentilators"),
            ["zone_hvac_equipment_lists"] = CountOsObjects(osModelType, osModel, "getZoneHVACEquipmentLists"),

            // Expanded Plant equipment counts
            ["chillers_absorption"] = SumGetters("getChillerAbsorptions", "getChillerAbsorptionIndirects"),
            ["cooling_towers_single_speed"] = CountOsObjects(osModelType, osModel, "getCoolingTowerSingleSpeeds"),
            ["cooling_towers_two_speed"] = CountOsObjects(osModelType, osModel, "getCoolingTowerTwoSpeeds"),
            ["fluid_coolers"] = SumGetters("getEvaporativeFluidCoolerSingleSpeeds", "getEvaporativeFluidCoolerTwoSpeeds"),
            ["district_cooling"] = CountOsObjects(osModelType, osModel, "getDistrictCoolings"),
            ["district_heating"] = SumGetters("getDistrictHeatingWaters", "getDistrictHeatingSteams"),
            ["heat_pumps_water_to_water"] = SumGetters("getHeatPumpWaterToWaterEquationFitCoolings", "getHeatPumpWaterToWaterEquationFitHeatings"),
            ["heat_pumps_plant_loop_eir"] = SumGetters("getHeatPumpPlantLoopEIRCoolings", "getHeatPumpPlantLoopEIRHeatings"),
            ["ground_heat_exchangers"] = SumGetters("getGroundHeatExchangerVerticals", "getGroundHeatExchangerHorizontalTrenchs"),
            ["heat_exchangers_fluid_to_fluid"] = CountOsObjects(osModelType, osModel, "getHeatExchangerFluidToFluids"),
            ["water_heaters"] = SumGetters("getWaterHeaterMixeds", "getWaterHeaterStratifieds", "getWaterHeaterHeatPumps"),
            ["pipes_adiabatic"] = CountOsObjects(osModelType, osModel, "getPipeAdiabatics"),

            // Controls, Sizing, Curves, Schedules, EMS, Generators, OutputVariables
            ["setpoint_managers"] = CountOsObjects(osModelType, osModel, "getSetpointManagers"),
            ["availability_managers"] = CountOsObjects(osModelType, osModel, "getAvailabilityManagers"),
            ["availability_manager_assignment_lists"] = CountOsObjects(osModelType, osModel, "getAvailabilityManagerAssignmentLists"),
            ["controllers_outdoor_air"] = CountOsObjects(osModelType, osModel, "getControllerOutdoorAirs"),
            ["controllers_water_coil"] = CountOsObjects(osModelType, osModel, "getControllerWaterCoils"),
            ["sizing_zones"] = CountOsObjects(osModelType, osModel, "getSizingZones"),
            ["sizing_systems"] = CountOsObjects(osModelType, osModel, "getSizingSystems"),
            ["sizing_plants"] = CountOsObjects(osModelType, osModel, "getSizingPlants"),
            ["curves"] = CountOsObjects(osModelType, osModel, "getCurves"),
            ["schedules"] = CountOsObjects(osModelType, osModel, "getSchedules"),
            ["ems_sensors"] = CountOsObjects(osModelType, osModel, "getEnergyManagementSystemSensors"),
            ["ems_actuators"] = CountOsObjects(osModelType, osModel, "getEnergyManagementSystemActuators"),
            ["ems_internal_variables"] = CountOsObjects(osModelType, osModel, "getEnergyManagementSystemInternalVariables"),
            ["ems_programs"] = CountOsObjects(osModelType, osModel, "getEnergyManagementSystemPrograms"),
            ["ems_program_calling_managers"] = CountOsObjects(osModelType, osModel, "getEnergyManagementSystemProgramCallingManagers"),
            ["ems_output_variables"] = CountOsObjects(osModelType, osModel, "getEnergyManagementSystemOutputVariables"),
            ["electric_load_center_distributions"] = CountOsObjects(osModelType, osModel, "getElectricLoadCenterDistributions"),
            ["generators"] = CountOsObjects(osModelType, osModel, "getGenerators"),
            ["output_variables"] = CountOsObjects(osModelType, osModel, "getOutputVariables"),
        };
    }

    private static Dictionary<string, object?> SummarizeSystem(Type sysType, object sys)
    {
        var displayName = sysType.GetProperty("DisplayName")?.GetValue(sys)?.ToString();
        var ibVersion = sysType.GetProperty("IBVersion")?.GetValue(sys)?.ToString();
        var airLoops = sysType.GetProperty("AirLoops")?.GetValue(sys) as IList;
        var plantLoops = sysType.GetProperty("PlantLoops")?.GetValue(sys) as IList;
        var vrfs = sysType.GetProperty("VariableRefrigerantFlows")?.GetValue(sys) as IList;
        var zoneNames = sysType.GetMethod("GetThermalZoneNames")?.Invoke(sys, null) as IEnumerable<string>;

        int realAirLoopCount = 0;
        int noAirLoopCount = 0;
        if (airLoops != null)
        {
            foreach (var loop in airLoops)
            {
                if (loop?.GetType().Name == "IB_NoAirLoop")
                    noAirLoopCount++;
                else if (loop != null)
                    realAirLoopCount++;
            }
        }

        return new Dictionary<string, object?>
        {
            ["display_name"] = displayName,
            ["ib_version"] = ibVersion,
            ["thermal_zones"] = zoneNames?.ToList() ?? new List<string>(),
            ["air_loop_count"] = realAirLoopCount,
            ["no_air_loop_count"] = noAirLoopCount,
            ["plant_loop_count"] = plantLoops?.Count ?? 0,
            ["vrf_count"] = vrfs?.Count ?? 0,
        };
    }

    private static int CountOsObjects(Type osModelType, object osModel, string getterName)
    {
        var method = osModelType.GetMethod(getterName, Type.EmptyTypes);
        if (method == null) return 0;
        var vec = method.Invoke(osModel, null);
        if (vec == null) return 0;
        var countProp = vec.GetType().GetProperty("Count");
        return countProp != null && countProp.GetValue(vec) is int c ? c : 0;
    }

    private static string GetRequiredString(JsonElement obj, string key)
    {
        if (!obj.TryGetProperty(key, out var el) || el.ValueKind != JsonValueKind.String || string.IsNullOrWhiteSpace(el.GetString()))
            throw new ArgumentException($"Missing required non-empty string property '{key}'.");
        return el.GetString()!.Trim();
    }

    private static string StripRefPrefix(string s)
    {
        s = s.Trim();
        return s.StartsWith("@", StringComparison.Ordinal) ? s[1..] : s;
    }

    private static bool IsNumericFieldType(Type? dataType)
    {
        if (dataType == null) return false;
        var underlying = Nullable.GetUnderlyingType(dataType) ?? dataType;
        return underlying == typeof(double)
            || underlying == typeof(float)
            || underlying == typeof(decimal)
            || underlying == typeof(int)
            || underlying == typeof(long)
            || underlying == typeof(short);
    }

    private static string NormalizeKey(string name)
    {
        return new string(name.Where(char.IsLetterOrDigit).ToArray()).ToLowerInvariant();
    }
}
