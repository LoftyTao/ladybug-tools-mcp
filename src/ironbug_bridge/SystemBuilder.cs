using System.Collections;
using System.Globalization;
using System.Reflection;
using System.Text.Json;

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

        // Build or resolve IB_ThermalZone instances keyed by room_name
        var zonesByRoom = new Dictionary<string, object>(StringComparer.Ordinal);
        if (draft.TryGetProperty("thermal_zones", out var tzListEl) && tzListEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var tzEl in tzListEl.EnumerateArray())
            {
                var roomName = GetRequiredString(tzEl, "room_name");
                if (zonesByRoom.ContainsKey(roomName))
                    throw new ArgumentException($"Duplicate thermal_zones entry for room_name '{roomName}'.");

                var zone = CreateThermalZone(roomName, tzEl, ResolveComponent);
                zonesByRoom[roomName] = zone;
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
                var airLoop = BuildAirLoop(alEl, ResolveComponent, zonesByRoom, assignedZoneRooms);
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
                var plantLoop = BuildPlantLoop(plEl, ResolveComponent);
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

    public Dictionary<string, object?> Validate(string specificationJson, IReadOnlyList<string> roomNames)
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

        var osModel = Activator.CreateInstance(osModelType)!;
        var setNameMethod = osZoneType.GetMethod("setName", new[] { typeof(string) });
        foreach (var zName in zoneNames)
        {
            var osZone = Activator.CreateInstance(osZoneType, new[] { osModel })!;
            setNameMethod?.Invoke(osZone, new object[] { zName });
        }

        var errors = new List<string>();
        var warnings = new List<string>();
        bool saveOk = false;

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

        var osSummary = new Dictionary<string, int>
        {
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
        };

        return new Dictionary<string, object?>
        {
            ["valid"] = saveOk && errors.Count == 0,
            ["errors"] = errors,
            ["warnings"] = warnings,
            ["thermal_zones"] = zoneNames.ToList(),
            ["system_summary"] = summary,
            ["openstudio_summary"] = osSummary,
        };
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

        if (spec.TryGetProperty("wiring", out var wiringEl) && wiringEl.ValueKind != JsonValueKind.Null && wiringEl.ValueKind != JsonValueKind.Undefined)
        {
            ApplyWiring(id, type, instance, wiringEl, resolveComponent, allSpecs);
        }

        if (spec.TryGetProperty("output_variables", out var outVarsEl) && outVarsEl.ValueKind == JsonValueKind.Array)
        {
            ApplyOutputVariables(id, type, instance, outVarsEl);
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
            var coerced = CoerceFieldValue(kv.Value, dataType, resolveComponent, allSpecs);
            tryAddMethod.Invoke(customAttrs, new[] { ibField, coerced });
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

    private object CreateThermalZone(string roomName, JsonElement tzEl, Func<string, object> resolveComponent)
    {
        var zoneType = _runtime.ResolveHvacType("IB_ThermalZone");
        var zone = Activator.CreateInstance(zoneType, new object[] { roomName })!;

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
        if (tzEl.TryGetProperty("zone_equipments", out var eqEl) && eqEl.ValueKind == JsonValueKind.Array)
        {
            var addEq = zoneType.GetMethod("AddZoneEquipment")!;
            foreach (var item in eqEl.EnumerateArray())
            {
                if (item.ValueKind != JsonValueKind.String)
                    throw new ArgumentException($"zone_equipments entries on room '{roomName}' must be component ID strings.");
                addEq.Invoke(zone, new[] { resolveComponent(StripRefPrefix(item.GetString()!)) });
            }
        }
        if (tzEl.TryGetProperty("allow_multi_air_loops", out var amaEl) && (amaEl.ValueKind == JsonValueKind.True || amaEl.ValueKind == JsonValueKind.False))
        {
            zoneType.GetProperty("AllowMultiAirLoops")?.SetValue(zone, amaEl.GetBoolean());
        }
        if (tzEl.TryGetProperty("supply_plenum", out var spEl) && spEl.ValueKind == JsonValueKind.String)
        {
            zoneType.GetMethod("SetSupplyPlenum")!.Invoke(zone, new[] { resolveComponent(StripRefPrefix(spEl.GetString()!)) });
        }
        if (tzEl.TryGetProperty("return_plenum", out var rpEl) && rpEl.ValueKind == JsonValueKind.String)
        {
            zoneType.GetMethod("SetReturnPlenum")!.Invoke(zone, new[] { resolveComponent(StripRefPrefix(rpEl.GetString()!)) });
        }
        return zone;
    }

    private object BuildAirLoop(
        JsonElement alEl,
        Func<string, object> resolveComponent,
        Dictionary<string, object> zonesByRoom,
        HashSet<string> assignedZoneRooms)
    {
        var alType = _runtime.ResolveHvacType("IB_AirLoopHVAC");
        var airLoop = Activator.CreateInstance(alType)!;

        if (alEl.TryGetProperty("name", out var nameEl) && nameEl.ValueKind == JsonValueKind.String)
        {
            SetFieldByName(alType, airLoop, "Name", nameEl.GetString()!);
        }

        if (alEl.TryGetProperty("sizing_system", out var szEl) && szEl.ValueKind == JsonValueKind.String)
        {
            alType.GetMethod("SetSizingSystem")!.Invoke(airLoop, new[] { resolveComponent(StripRefPrefix(szEl.GetString()!)) });
        }

        var addToSupply = alType.GetMethod("AddToSupplySide")!;
        if (alEl.TryGetProperty("supply", out var supEl) && supEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in supEl.EnumerateArray())
            {
                if (item.ValueKind != JsonValueKind.String)
                    throw new ArgumentException("air_loops[].supply items must be component ID strings.");
                addToSupply.Invoke(airLoop, new[] { resolveComponent(StripRefPrefix(item.GetString()!)) });
            }
        }

        object GetOrCreateZoneByRoom(string roomOrCompId)
        {
            var key = StripRefPrefix(roomOrCompId);
            if (zonesByRoom.TryGetValue(key, out var z))
            {
                assignedZoneRooms.Add(key);
                return z;
            }
            // Also check if it's a component ID of an IB_ThermalZone in components
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
                var arr = Array.CreateInstance(hvacObjBase, 1);
                arr.SetValue(zoneObj, 0);
                addBranchMethod.Invoke(ab, new object[] { arr });
            }
            addToDemand.Invoke(airLoop, new[] { ab });
        }

        return airLoop;
    }

    private object BuildPlantLoop(JsonElement plEl, Func<string, object> resolveComponent)
    {
        var plType = _runtime.ResolveHvacType("IB_PlantLoop");
        var plantLoop = Activator.CreateInstance(plType)!;

        if (plEl.TryGetProperty("name", out var nameEl) && nameEl.ValueKind == JsonValueKind.String)
        {
            SetFieldByName(plType, plantLoop, "Name", nameEl.GetString()!);
        }

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

        var addToSupply = plType.GetMethod("AddToSupply")!;
        var addToDemand = plType.GetMethod("AddToDemand")!;

        object BuildPlantBranches(JsonElement branchesEl, string sideName)
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
            return branches;
        }

        // Supply side: serial items (pump, etc.) + parallel supply_branches + optional setpoint
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
                    addToSupply.Invoke(plantLoop, new[] { BuildPlantBranches(item, "supply") });
                }
                else
                {
                    throw new ArgumentException("plant_loops[].supply items must be component IDs or branch lists.");
                }
            }
        }
        if (plEl.TryGetProperty("supply_branches", out var sbEl) && sbEl.ValueKind == JsonValueKind.Array)
        {
            addToSupply.Invoke(plantLoop, new[] { BuildPlantBranches(sbEl, "supply_branches") });
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

        // Demand side
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
                    addToDemand.Invoke(plantLoop, new[] { BuildPlantBranches(item, "demand") });
                }
                else
                {
                    throw new ArgumentException("plant_loops[].demand items must be component IDs or branch lists.");
                }
            }
        }
        if (plEl.TryGetProperty("demand_branches", out var dbEl) && dbEl.ValueKind == JsonValueKind.Array)
        {
            addToDemand.Invoke(plantLoop, new[] { BuildPlantBranches(dbEl, "demand_branches") });
        }

        return plantLoop;
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

    private object? CoerceFieldValue(
        JsonElement el,
        Type? targetType,
        Func<string, object> resolveComponent,
        Dictionary<string, JsonElement> allSpecs)
    {
        if (el.ValueKind == JsonValueKind.Null) return null;

        if (el.ValueKind == JsonValueKind.String)
        {
            var s = el.GetString()!;
            var stripped = StripRefPrefix(s);
            bool explicitRef = s.StartsWith("@", StringComparison.Ordinal);
            bool expectsModelObj = targetType != null && targetType.Namespace != null && targetType.Namespace.StartsWith("OpenStudio", StringComparison.Ordinal);
            if ((explicitRef || expectsModelObj) && allSpecs.ContainsKey(stripped))
            {
                return resolveComponent(stripped);
            }
            if (targetType == typeof(double) && double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var d))
                return d;
            if (targetType == typeof(int) && int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var iv))
                return iv;
            if (targetType == typeof(bool) && bool.TryParse(s, out var bv))
                return bv;
            return s;
        }

        if (el.ValueKind == JsonValueKind.Number)
        {
            if (targetType == typeof(int)) return el.GetInt32();
            return el.GetDouble();
        }
        if (el.ValueKind == JsonValueKind.True || el.ValueKind == JsonValueKind.False)
        {
            return el.GetBoolean();
        }
        throw new ArgumentException($"Unsupported field value kind: {el.ValueKind}");
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
