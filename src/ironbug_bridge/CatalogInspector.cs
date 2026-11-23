using System.Collections;
using System.Collections.Immutable;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Text.RegularExpressions;

namespace IronbugBridge;

/// <summary>
/// Reflects Ironbug.HVAC component classes, constructors, wiring methods, and
/// *_FieldSet + Ironbug.EPDoc metadata on demand.
/// </summary>
internal sealed class CatalogInspector
{
    private static readonly HashSet<string> ExcludedClassNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "IB_HVACSystem",
        "IB_ModelObject",
        "IB_HVACObject",
        "IB_Field",
        "IB_Field_Comment",
        "IB_Field_Name",
        "IB_BasicField",
        "IB_TopField",
        "IB_IddField",
        "IB_FieldArgument",
        "IB_FieldArgumentSet",
        "IB_PropArgumentSet",
        "IB_Children",
        "IB_ExistingObj",
        "IB_ExistAirLoop",
        "IB_ExistPlantLoop",
        "IB_LoopBranches",
        "IB_PlantLoopBranches",
        "IB_AirLoopBranches",
        "IB_NoAirLoop",
        "IB_OutputVariable",
    };

    private static readonly HashSet<string> BasePlumbingMethods = new(StringComparer.OrdinalIgnoreCase)
    {
        "AddCustomAttribute",
        "AddOutputVariables",
        "AddEMSSensors",
        "AddEMSInternalVariables",
        "AddEMSActuators",
        "Set",
        "SetTrackingID",
        "SetRefObject",
        "SetFieldValue",
        "SetFieldValues",
        "IsInModel",
        "GetOsmObjInModel",
        "ApplyAttributesToObj",
        "ToJson",
        "Duplicate",
        "ToString",
        "ToStrings",
        "Equals",
        "GetHashCode",
        "ToOS",
        "ToOS_NoAirLoop",
        "ToOS_Supply",
        "ToOS_Demand",
        "AddToNode",
        "GetChild",
        "GetTrackingID",
        "GetTrackingTagID",
        "GetThermalZones",
        "GetThermalZoneNames",
    };

    private readonly BridgeRuntime _runtime;
    private readonly object _metadataLock = new();
    private MetadataCatalog? _metadataCache;

    public CatalogInspector(BridgeRuntime runtime)
    {
        _runtime = runtime;
    }

    public static string Categorize(Type t)
    {
        return Categorize(t.Name, t.BaseType?.Name);
    }

    public static string Categorize(string name, string? baseNameRaw)
    {
        var baseName = baseNameRaw ?? string.Empty;

        if (name == "IB_ThermalZone") return "thermal_zone";
        if (baseName == "IB_ZoneEquipment" || name.StartsWith("IB_ZoneHVAC", StringComparison.Ordinal) || name.StartsWith("IB_WaterHeater", StringComparison.Ordinal) || name == "IB_FanZoneExhaust" || name == "IB_ZoneEquipmentGroup")
            return "zone_equipment";
        if (baseName == "IB_AirTerminal" || name.StartsWith("IB_AirTerminal", StringComparison.Ordinal))
            return "air_terminal";
        if (baseName == "IB_CoilDX" || (name.Contains("Coil", StringComparison.Ordinal) && name.Contains("DX", StringComparison.Ordinal)))
            return "coil_dx";
        if (baseName == "IB_CoilCoolingBasic" || name.StartsWith("IB_CoilCooling", StringComparison.Ordinal))
            return "coil_cooling";
        if (baseName == "IB_CoilHeatingBasic" || name.StartsWith("IB_CoilHeating", StringComparison.Ordinal) || baseName == "IB_Coil" || name.StartsWith("IB_Coil", StringComparison.Ordinal))
            return "coil_heating";
        if (baseName == "IB_Fan" || name.StartsWith("IB_Fan", StringComparison.Ordinal))
            return "fan";
        if (baseName == "IB_Pump" || name.StartsWith("IB_Pump", StringComparison.Ordinal))
            return "pump";
        if (baseName == "IB_SetpointManager" || name.StartsWith("IB_SetpointManager", StringComparison.Ordinal))
            return "setpoint_manager";
        if (baseName == "IB_AvailabilityManager" || name.StartsWith("IB_AvailabilityManager", StringComparison.Ordinal))
            return "availability_manager";
        if (baseName == "IB_Curve" || name.StartsWith("IB_Curve", StringComparison.Ordinal))
            return "curve";
        if (baseName == "IB_Schedule" || name.StartsWith("IB_Schedule", StringComparison.Ordinal))
            return "schedule";
        if (baseName == "IB_VRFSystem" || name.Contains("VariableRefrigerantFlow", StringComparison.Ordinal))
            return "vrf";
        if (name.StartsWith("IB_Sizing", StringComparison.Ordinal))
            return "sizing";
        if (name.StartsWith("IB_Controller", StringComparison.Ordinal))
            return "controller";
        if (name.StartsWith("IB_EnergyManagementSystem", StringComparison.Ordinal) || baseName.StartsWith("IB_EnergyManagementSystem", StringComparison.Ordinal))
            return "ems";
        if (baseName is "IB_Generator" or "IB_ElecInverter" or "IB_ElecStorage" or "IB_PhotovoltaicPerformance" or "IB_SolarCollectorPerformancePhotovoltaicThermal"
            || name.StartsWith("IB_Generator", StringComparison.Ordinal) || name.StartsWith("IB_ElectricLoadCenter", StringComparison.Ordinal) || name.StartsWith("IB_Photovoltaic", StringComparison.Ordinal))
            return "generator_electric";
        if (name.StartsWith("IB_AirLoop", StringComparison.Ordinal) || baseName == "IB_AirLoopHVAC" || baseName == "IB_AirLoopHVACUnitary"
            || name.StartsWith("IB_OutdoorAir", StringComparison.Ordinal) || name.StartsWith("IB_HeatExchangerAirToAir", StringComparison.Ordinal)
            || name.StartsWith("IB_EvaporativeCooler", StringComparison.Ordinal) || name.StartsWith("IB_Humidifier", StringComparison.Ordinal))
            return "air_loop";
        if (name.StartsWith("IB_PlantLoop", StringComparison.Ordinal) || baseName == "IB_PlantLoop" || baseName == "IB_PlantEquipmentOperationSchemeBase" || name.StartsWith("IB_PlantEquipmentOperation", StringComparison.Ordinal))
            return "plant_loop";
        if (name.StartsWith("IB_Chiller", StringComparison.Ordinal) || name.StartsWith("IB_Boiler", StringComparison.Ordinal)
            || name.StartsWith("IB_CoolingTower", StringComparison.Ordinal) || name.StartsWith("IB_FluidCooler", StringComparison.Ordinal)
            || name.StartsWith("IB_EvaporativeFluidCooler", StringComparison.Ordinal) || name.StartsWith("IB_District", StringComparison.Ordinal)
            || name.StartsWith("IB_HeatPumpPlantLoop", StringComparison.Ordinal) || name.StartsWith("IB_CentralHeatPump", StringComparison.Ordinal)
            || name.StartsWith("IB_ThermalStorage", StringComparison.Ordinal) || name.StartsWith("IB_HeatExchangerFluidToFluid", StringComparison.Ordinal)
            || name.StartsWith("IB_GroundHeatExchanger", StringComparison.Ordinal) || name.StartsWith("IB_Pipe", StringComparison.Ordinal)
            || name.StartsWith("IB_TemperingValve", StringComparison.Ordinal) || name.StartsWith("IB_HeaderedPumps", StringComparison.Ordinal)
            || name.StartsWith("IB_SolarCollector", StringComparison.Ordinal) || name.StartsWith("IB_WaterUse", StringComparison.Ordinal))
            return "plant_equipment";
        return "other";
    }

    private IEnumerable<Type> EnumerateCatalogTypes()
    {
        return _runtime.GetAllHvacTypes()
            .Where(t =>
                t.IsClass
                && !t.IsAbstract
                && t.Name.StartsWith("IB_", StringComparison.Ordinal)
                && !t.Name.EndsWith("_FieldSet", StringComparison.Ordinal)
                && !ExcludedClassNames.Contains(t.Name))
            .OrderBy(t => t.Name, StringComparer.Ordinal);
    }

    public Dictionary<string, object?> Catalog(string? category, string? query, int limit, int offset = 0)
    {
        if (!_runtime.HasOpenStudio)
        {
            var meta = GetMetadataCatalog();
            return ScoreAndPaginateCatalog(
                meta.CatalogTypes,
                t => t.Name,
                t => t.BaseName,
                t => BridgeRuntime.GetEpdocNote(_runtime.ResolveEpdocTypeByName(t.Name)) ?? $"{t.Name} ({t.BaseName})",
                category,
                query,
                limit,
                offset);
        }

        var all = EnumerateCatalogTypes().ToList();
        return ScoreAndPaginateCatalog(
            all,
            t => t.Name,
            t => t.BaseType?.Name,
            GetTypeSummary,
            category,
            query,
            limit,
            offset);
    }

    private static Dictionary<string, object?> ScoreAndPaginateCatalog<T>(
        IReadOnlyList<T> all,
        Func<T, string> getName,
        Func<T, string?> getBaseName,
        Func<T, string> getSummary,
        string? category,
        string? query,
        int limit,
        int offset)
    {
        var categoryCounts = new SortedDictionary<string, int>(StringComparer.Ordinal);
        foreach (var t in all)
        {
            var cat = Categorize(getName(t), getBaseName(t));
            categoryCounts[cat] = categoryCounts.GetValueOrDefault(cat) + 1;
        }

        int skip = Math.Max(0, offset);
        IEnumerable<T> filtered = all;
        if (!string.IsNullOrWhiteSpace(category))
        {
            var catNorm = category.Trim().ToLowerInvariant();
            if (!categoryCounts.ContainsKey(catNorm))
            {
                return new Dictionary<string, object?>
                {
                    ["total_catalog_types"] = all.Count,
                    ["total_matched"] = 0,
                    ["offset"] = skip,
                    ["truncated"] = false,
                    ["unknown_category"] = catNorm,
                    ["valid_categories"] = categoryCounts.Keys.ToList(),
                    ["categories"] = categoryCounts,
                    ["matches"] = new List<Dictionary<string, object?>>(),
                };
            }
            filtered = filtered.Where(t => Categorize(getName(t), getBaseName(t)) == catNorm);
        }

        var rawQuery = (query ?? string.Empty).Trim().ToLowerInvariant();
        var strippedQuery = rawQuery.StartsWith("ib_", StringComparison.Ordinal) ? rawQuery[3..] : rawQuery;
        var rawTokens = string.IsNullOrWhiteSpace(strippedQuery)
            ? Array.Empty<string>()
            : strippedQuery.Split(new[] { ' ', '_', '-', ',', ':', '/' }, StringSplitOptions.RemoveEmptyEntries);
        var tokens = rawTokens.Where(tok => tok != "ib").ToArray();
        if (tokens.Length == 0 && rawTokens.Length > 0)
        {
            tokens = rawTokens;
        }

        var scored = new List<(int Score, bool AllMatched, T Item, string Name, string? BaseName, string Summary)>();
        foreach (var t in filtered)
        {
            var name = getName(t);
            var baseName = getBaseName(t);
            var summary = getSummary(t);
            var cat = Categorize(name, baseName);
            if (tokens.Length == 0)
            {
                scored.Add((0, true, t, name, baseName, summary));
                continue;
            }

            var nameLower = name.ToLowerInvariant();
            var nameWithoutPrefix = nameLower.StartsWith("ib_", StringComparison.Ordinal) ? nameLower[3..] : nameLower;
            var summaryLower = summary.ToLowerInvariant();

            if (!string.IsNullOrEmpty(strippedQuery)
                && (nameLower == rawQuery || nameLower == "ib_" + strippedQuery || nameWithoutPrefix == strippedQuery))
            {
                scored.Add((1000, true, t, name, baseName, summary));
                continue;
            }

            int score = 0;
            bool allMatched = true;
            foreach (var tok in tokens)
            {
                if (nameLower == tok || nameWithoutPrefix == tok)
                    score += 100;
                else if (nameLower.Contains(tok, StringComparison.Ordinal))
                    score += 20;
                else if (cat.Contains(tok, StringComparison.Ordinal))
                    score += 10;
                else if (summaryLower.Contains(tok, StringComparison.Ordinal))
                    score += 5;
                else
                    allMatched = false;
            }

            if (allMatched || score >= 20)
            {
                int bonus = allMatched ? 50 : 0;
                scored.Add((score + bonus, allMatched, t, name, baseName, summary));
            }
        }

        var active = scored;
        if (tokens.Length > 0)
        {
            var exactOrAll = scored.Where(x => x.AllMatched).ToList();
            if (exactOrAll.Count > 0)
            {
                active = exactOrAll;
            }
        }

        var ordered = tokens.Length > 0
            ? active.OrderByDescending(x => x.Score).ThenBy(x => x.Name.Length).ThenBy(x => x.Name, StringComparer.Ordinal)
            : active.OrderBy(x => x.Name, StringComparer.Ordinal);

        var cap = Math.Clamp(limit > 0 ? limit : 25, 1, 100);
        var matches = ordered.Skip(skip).Take(cap).Select(x => new Dictionary<string, object?>
        {
            ["type_name"] = x.Name,
            ["category"] = Categorize(x.Name, x.BaseName),
            ["base_type"] = x.BaseName,
            ["summary"] = Truncate(x.Summary, 160),
        }).ToList();

        return new Dictionary<string, object?>
        {
            ["total_catalog_types"] = all.Count,
            ["total_matched"] = active.Count,
            ["offset"] = skip,
            ["truncated"] = (skip + matches.Count) < active.Count,
            ["categories"] = categoryCounts,
            ["matches"] = matches,
        };
    }

    public Dictionary<string, object?> Describe(IEnumerable<string> typeNames, bool includeAdvanced)
    {
        if (!_runtime.HasOpenStudio)
        {
            return DescribeFromMetadata(typeNames, includeAdvanced);
        }

        var items = new List<Dictionary<string, object?>>();
        var notFound = new List<string>();

        foreach (var rawName in typeNames)
        {
            Type? t = null;
            try
            {
                t = _runtime.ResolveHvacType(rawName);
            }
            catch (KeyNotFoundException)
            {
                notFound.Add(rawName);
                continue;
            }

            items.Add(DescribeOne(t, includeAdvanced));
        }

        return new Dictionary<string, object?>
        {
            ["components"] = items,
            ["not_found"] = notFound,
        };
    }

    private Dictionary<string, object?> DescribeFromMetadata(IEnumerable<string> typeNames, bool includeAdvanced)
    {
        var meta = GetMetadataCatalog();
        var items = new List<Dictionary<string, object?>>();
        var notFound = new List<string>();

        foreach (var rawName in typeNames)
        {
            var info = meta.ResolveType(rawName);
            if (info == null)
            {
                notFound.Add(rawName);
                continue;
            }
            items.Add(DescribeOneMetadata(meta, info, includeAdvanced));
        }

        return new Dictionary<string, object?>
        {
            ["components"] = items,
            ["not_found"] = notFound,
        };
    }

    private Dictionary<string, object?> DescribeOneMetadata(
        MetadataCatalog meta,
        MetadataTypeInfo info,
        bool includeAdvanced)
    {
        var epdocType = _runtime.ResolveEpdocTypeByName(info.Name);
        var summary = BridgeRuntime.GetEpdocNote(epdocType) ?? $"{info.Name} ({info.BaseName})";
        bool instantiable = !info.IsAbstract && !ExcludedClassNames.Contains(info.Name);

        var constructors = info.Constructors
            .Where(c => !c.Parameters.Any(p => p.IsDelegateLike))
            .Select(c => new Dictionary<string, object?>
            {
                ["parameters"] = c.Parameters.Select(p => new Dictionary<string, object?>
                {
                    ["name"] = p.Name,
                    ["type"] = p.Type,
                    ["required"] = p.Required,
                    ["default"] = p.Default,
                }).ToList(),
            })
            .ToList();

        var wiringMethods = new List<Dictionary<string, object?>>();
        var seenWiring = new HashSet<string>(StringComparer.Ordinal);
        MetadataTypeInfo? cursor = info;
        int depth = 0;
        while (cursor != null && depth++ < 32)
        {
            if (cursor.Name is "Object" or "IB_ModelObject" or "IB_HVACObject")
                break;

            foreach (var m in cursor.DeclaredWiringMethods)
            {
                var key = m.Name + "(" + string.Join(",", m.Parameters.Select(p => p.RawTypeName)) + ")";
                if (!seenWiring.Add(key)) continue;
                wiringMethods.Add(new Dictionary<string, object?>
                {
                    ["method"] = m.Name,
                    ["slot_alias"] = ToSnakeCase(m.Name[3..]),
                    ["parameters"] = m.Parameters.Select(p => new Dictionary<string, object?>
                    {
                        ["name"] = p.Name,
                        ["type"] = p.Type,
                    }).ToList(),
                });
            }

            cursor = meta.ResolveBase(cursor);
        }

        var coreFields = new List<Dictionary<string, object?>>();
        var advancedFields = new List<Dictionary<string, object?>>();
        var coreNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        var fsInfo = meta.ResolveFieldSet(info);
        if (fsInfo != null)
        {
            foreach (var propName in fsInfo.DeclaredPropertyNames)
            {
                if (propName is "OwnerEpNote" or "Count" or "IsReadOnly") continue;
                coreNames.Add(propName);
                coreFields.Add(BuildMetadataFieldInfo(propName, epdocType));
            }
        }

        if (epdocType != null)
        {
            foreach (var f in epdocType.GetFields(BindingFlags.Public | BindingFlags.Static))
            {
                if (!f.Name.StartsWith("Field_", StringComparison.Ordinal)) continue;
                var fieldName = f.Name["Field_".Length..];
                if (string.IsNullOrEmpty(fieldName) || coreNames.Contains(fieldName)) continue;
                var epDesc = f.GetValue(null)?.ToString()?.Trim();
                advancedFields.Add(BuildMetadataFieldInfo(fieldName, epdocType, epDesc));
            }
        }

        var result = new Dictionary<string, object?>
        {
            ["type_name"] = info.Name,
            ["instantiable"] = instantiable,
            ["category"] = Categorize(info.Name, info.BaseName),
            ["base_type"] = info.BaseName,
            ["summary"] = Truncate(summary, 800),
            ["constructors"] = constructors,
            ["wiring_methods"] = wiringMethods,
            ["core_fields"] = coreFields,
            ["advanced_field_count"] = advancedFields.Count,
        };
        if (!instantiable)
        {
            result["concrete_subclasses"] = meta.CatalogTypes
                .Where(c => meta.IsAssignableFrom(info, c))
                .Select(c => c.Name)
                .Take(25)
                .ToList();
        }
        if (includeAdvanced)
        {
            result["advanced_fields"] = advancedFields;
        }
        return result;
    }

    private static Dictionary<string, object?> BuildMetadataFieldInfo(
        string fieldName,
        Type? epdocType,
        string? preloadedDesc = null)
    {
        var desc = preloadedDesc ?? BridgeRuntime.GetEpdocFieldDescription(epdocType, fieldName) ?? "";
        var normalizedUnit = ExtractUnitFromText(desc);
        var defaultVal = ExtractDefaultFromText(desc);

        string inferredType = "any";
        if (string.Equals(fieldName, "Name", StringComparison.OrdinalIgnoreCase))
            inferredType = "string";
        else if (!string.IsNullOrWhiteSpace(normalizedUnit))
            inferredType = "number";
        else if (desc.Contains("numeric field", StringComparison.OrdinalIgnoreCase))
            inferredType = "number";
        else if (desc.Contains("alpha field", StringComparison.OrdinalIgnoreCase))
            inferredType = "string";

        var dict = new Dictionary<string, object?>
        {
            ["name"] = fieldName,
            ["type"] = inferredType,
        };
        if (!string.IsNullOrWhiteSpace(normalizedUnit))
            dict["unit"] = normalizedUnit;
        if (!string.IsNullOrWhiteSpace(defaultVal))
            dict["default"] = defaultVal;
        if (!string.IsNullOrWhiteSpace(desc))
            dict["description"] = Truncate(desc.Replace("\r", " ").Replace("\n", " "), 500);
        return dict;
    }

    private MetadataCatalog GetMetadataCatalog()
    {
        lock (_metadataLock)
        {
            if (_metadataCache != null) return _metadataCache;
            _metadataCache = BuildMetadataCatalog(_runtime.HvacAssemblyPath);
            return _metadataCache;
        }
    }

    private static MetadataCatalog BuildMetadataCatalog(string hvacDllPath)
    {
        if (!File.Exists(hvacDllPath))
        {
            throw new FileNotFoundException($"Ironbug.HVAC.dll not found at {hvacDllPath}", hvacDllPath);
        }

        using var fs = File.OpenRead(hvacDllPath);
        using var peReader = new PEReader(fs);
        var mr = peReader.GetMetadataReader();
        var provider = new MetadataSignatureTypeProvider();

        var types = new List<MetadataTypeInfo>();
        var byName = new Dictionary<string, MetadataTypeInfo>(StringComparer.OrdinalIgnoreCase);
        var byFullName = new Dictionary<string, MetadataTypeInfo>(StringComparer.OrdinalIgnoreCase);
        var delegateFullNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        // Pass 1: collect type definitions so delegate detection works reliably.
        var rawTypes = new List<(TypeDefinitionHandle Handle, TypeDefinition Td, MetadataTypeInfo Info)>();
        foreach (var h in mr.TypeDefinitions)
        {
            var td = mr.GetTypeDefinition(h);
            var name = mr.GetString(td.Name);
            var ns = mr.GetString(td.Namespace);
            var fullName = string.IsNullOrEmpty(ns) ? name : $"{ns}.{name}";

            string? baseName = null;
            string? baseFullName = null;
            if (!td.BaseType.IsNil)
            {
                if (td.BaseType.Kind == HandleKind.TypeDefinition)
                {
                    var btd = mr.GetTypeDefinition((TypeDefinitionHandle)td.BaseType);
                    baseName = mr.GetString(btd.Name);
                    var bns = mr.GetString(btd.Namespace);
                    baseFullName = string.IsNullOrEmpty(bns) ? baseName : $"{bns}.{baseName}";
                }
                else if (td.BaseType.Kind == HandleKind.TypeReference)
                {
                    var btr = mr.GetTypeReference((TypeReferenceHandle)td.BaseType);
                    baseName = mr.GetString(btr.Name);
                    var bns = mr.GetString(btr.Namespace);
                    baseFullName = string.IsNullOrEmpty(bns) ? baseName : $"{bns}.{baseName}";
                }
            }

            bool isPublic = (td.Attributes & TypeAttributes.VisibilityMask) == TypeAttributes.Public;
            bool isClass = (td.Attributes & TypeAttributes.ClassSemanticsMask) == TypeAttributes.Class;
            bool isAbstract = (td.Attributes & TypeAttributes.Abstract) != 0;
            bool isDelegate = baseName is "MulticastDelegate" or "Delegate";
            if (isDelegate)
            {
                delegateFullNames.Add(fullName);
                delegateFullNames.Add(name);
            }

            var info = new MetadataTypeInfo(name, fullName, baseName, baseFullName, isPublic, isClass, isAbstract);
            types.Add(info);
            byName.TryAdd(name, info);
            byFullName.TryAdd(fullName, info);
            rawTypes.Add((h, td, info));
        }

        // Pass 2: decode constructors, Set*/Add* wiring methods, and *_FieldSet properties.
        foreach (var (_, td, info) in rawTypes)
        {
            if (!info.IsPublic || !info.IsClass) continue;

            foreach (var mh in td.GetMethods())
            {
                var md = mr.GetMethodDefinition(mh);
                if ((md.Attributes & MethodAttributes.MemberAccessMask) != MethodAttributes.Public) continue;
                if ((md.Attributes & MethodAttributes.Static) != 0) continue;

                var mName = mr.GetString(md.Name);
                bool isCtor = mName == ".ctor";
                bool isWiring = !isCtor
                    && (md.Attributes & MethodAttributes.SpecialName) == 0
                    && !BasePlumbingMethods.Contains(mName)
                    && !mName.StartsWith("ShouldSerialize", StringComparison.Ordinal)
                    && !mName.StartsWith("ToOS", StringComparison.Ordinal)
                    && (mName.StartsWith("Set", StringComparison.Ordinal) || mName.StartsWith("Add", StringComparison.Ordinal));

                if (!isCtor && !isWiring) continue;

                MethodSignature<SigTypeInfo> sig;
                try
                {
                    sig = md.DecodeSignature(provider, null);
                }
                catch
                {
                    continue;
                }

                var paramInfos = new MetadataParamInfo[sig.ParameterTypes.Length];
                for (int i = 0; i < paramInfos.Length; i++)
                {
                    var st = sig.ParameterTypes[i];
                    paramInfos[i] = new MetadataParamInfo(
                        $"arg{i}",
                        st.FriendlyName,
                        st.RawTypeName,
                        true,
                        null,
                        IsDelegateType(st, delegateFullNames));
                }

                foreach (var ph in md.GetParameters())
                {
                    var p = mr.GetParameter(ph);
                    int idx = p.SequenceNumber - 1;
                    if (idx < 0 || idx >= paramInfos.Length) continue;

                    var pName = mr.GetString(p.Name);
                    bool isOpt = (p.Attributes & ParameterAttributes.Optional) != 0;
                    bool hasDefault = (p.Attributes & ParameterAttributes.HasDefault) != 0;
                    object? defVal = null;
                    if (hasDefault)
                    {
                        var ch = p.GetDefaultValue();
                        if (!ch.IsNil)
                        {
                            defVal = ReadMetadataConstant(mr, ch);
                        }
                    }

                    var cur = paramInfos[idx];
                    paramInfos[idx] = cur with
                    {
                        Name = string.IsNullOrEmpty(pName) ? cur.Name : pName,
                        Required = !(isOpt || hasDefault),
                        Default = (isOpt || hasDefault) ? SafeDefault(defVal) : null,
                    };
                }

                var methodInfo = new MetadataMethodInfo(mName, paramInfos.ToList());
                if (isCtor)
                    info.Constructors.Add(methodInfo);
                else
                    info.DeclaredWiringMethods.Add(methodInfo);
            }

            if (info.Name.EndsWith("_FieldSet", StringComparison.Ordinal))
            {
                foreach (var ph in td.GetProperties())
                {
                    var pd = mr.GetPropertyDefinition(ph);
                    var acc = pd.GetAccessors();
                    if (acc.Getter.IsNil) continue;
                    var getter = mr.GetMethodDefinition(acc.Getter);
                    if ((getter.Attributes & MethodAttributes.MemberAccessMask) != MethodAttributes.Public) continue;
                    if ((getter.Attributes & MethodAttributes.Static) != 0) continue;
                    info.DeclaredPropertyNames.Add(mr.GetString(pd.Name));
                }
            }
        }

        var catalogTypes = types
            .Where(t =>
                t.IsPublic
                && t.IsClass
                && !t.IsAbstract
                && t.Name.StartsWith("IB_", StringComparison.Ordinal)
                && !t.Name.EndsWith("_FieldSet", StringComparison.Ordinal)
                && !ExcludedClassNames.Contains(t.Name))
            .OrderBy(t => t.Name, StringComparer.Ordinal)
            .ToList();

        return new MetadataCatalog(catalogTypes, byName, byFullName);
    }

    private static bool IsDelegateType(SigTypeInfo st, HashSet<string> delegateFullNames)
    {
        return st.RawTypeName is "Delegate" or "MulticastDelegate" or "Action" or "Func"
            || st.RawTypeName.StartsWith("Action`", StringComparison.Ordinal)
            || st.RawTypeName.StartsWith("Func`", StringComparison.Ordinal)
            || delegateFullNames.Contains(st.RawTypeName);
    }

    private static object? ReadMetadataConstant(MetadataReader mr, ConstantHandle ch)
    {
        var c = mr.GetConstant(ch);
        var br = mr.GetBlobReader(c.Value);
        return c.TypeCode switch
        {
            ConstantTypeCode.Boolean => br.ReadBoolean(),
            ConstantTypeCode.Char => br.ReadChar(),
            ConstantTypeCode.SByte => br.ReadSByte(),
            ConstantTypeCode.Byte => br.ReadByte(),
            ConstantTypeCode.Int16 => br.ReadInt16(),
            ConstantTypeCode.UInt16 => br.ReadUInt16(),
            ConstantTypeCode.Int32 => br.ReadInt32(),
            ConstantTypeCode.UInt32 => br.ReadUInt32(),
            ConstantTypeCode.Int64 => br.ReadInt64(),
            ConstantTypeCode.UInt64 => br.ReadUInt64(),
            ConstantTypeCode.Single => br.ReadSingle(),
            ConstantTypeCode.Double => br.ReadDouble(),
            ConstantTypeCode.String => br.ReadUTF16(br.Length),
            ConstantTypeCode.NullReference => null,
            _ => null,
        };
    }

    private sealed record SigTypeInfo(string FriendlyName, string RawTypeName);

    private sealed record MetadataParamInfo(
        string Name,
        string Type,
        string RawTypeName,
        bool Required,
        object? Default,
        bool IsDelegateLike);

    private sealed record MetadataMethodInfo(string Name, List<MetadataParamInfo> Parameters);

    private sealed class MetadataTypeInfo
    {
        public string Name { get; }
        public string FullName { get; }
        public string? BaseName { get; }
        public string? BaseFullName { get; }
        public bool IsPublic { get; }
        public bool IsClass { get; }
        public bool IsAbstract { get; }
        public List<MetadataMethodInfo> Constructors { get; } = new();
        public List<MetadataMethodInfo> DeclaredWiringMethods { get; } = new();
        public List<string> DeclaredPropertyNames { get; } = new();

        public MetadataTypeInfo(
            string name,
            string fullName,
            string? baseName,
            string? baseFullName,
            bool isPublic,
            bool isClass,
            bool isAbstract)
        {
            Name = name;
            FullName = fullName;
            BaseName = baseName;
            BaseFullName = baseFullName;
            IsPublic = isPublic;
            IsClass = isClass;
            IsAbstract = isAbstract;
        }
    }

    private sealed class MetadataCatalog
    {
        public List<MetadataTypeInfo> CatalogTypes { get; }
        private readonly Dictionary<string, MetadataTypeInfo> _byName;
        private readonly Dictionary<string, MetadataTypeInfo> _byFullName;

        public MetadataCatalog(
            List<MetadataTypeInfo> catalogTypes,
            Dictionary<string, MetadataTypeInfo> byName,
            Dictionary<string, MetadataTypeInfo> byFullName)
        {
            CatalogTypes = catalogTypes;
            _byName = byName;
            _byFullName = byFullName;
        }

        public MetadataTypeInfo? ResolveType(string rawName)
        {
            if (_byName.TryGetValue(rawName, out var exact)) return exact;
            if (_byFullName.TryGetValue(rawName, out var full)) return full;
            if (!rawName.StartsWith("IB_", StringComparison.OrdinalIgnoreCase)
                && _byName.TryGetValue("IB_" + rawName, out var prefixed))
            {
                return prefixed;
            }
            return null;
        }

        public MetadataTypeInfo? ResolveBase(MetadataTypeInfo info)
        {
            if (!string.IsNullOrEmpty(info.BaseFullName) && _byFullName.TryGetValue(info.BaseFullName, out var bFull))
                return bFull;
            if (!string.IsNullOrEmpty(info.BaseName) && _byName.TryGetValue(info.BaseName, out var bName))
                return bName;
            return null;
        }

        public MetadataTypeInfo? ResolveFieldSet(MetadataTypeInfo info)
        {
            if (_byName.TryGetValue(info.Name + "_FieldSet", out var direct)) return direct;
            if (_byFullName.TryGetValue(info.FullName + "_FieldSet", out var full)) return full;
            return null;
        }

        public bool IsAssignableFrom(MetadataTypeInfo baseInfo, MetadataTypeInfo candidate)
        {
            MetadataTypeInfo? cursor = candidate;
            int depth = 0;
            while (cursor != null && depth++ < 32)
            {
                if (string.Equals(cursor.FullName, baseInfo.FullName, StringComparison.OrdinalIgnoreCase))
                    return true;
                cursor = ResolveBase(cursor);
            }
            return false;
        }
    }

    private sealed class MetadataSignatureTypeProvider : ISignatureTypeProvider<SigTypeInfo, object?>
    {
        public SigTypeInfo GetPrimitiveType(PrimitiveTypeCode typeCode) => typeCode switch
        {
            PrimitiveTypeCode.Boolean => new("boolean", "Boolean"),
            PrimitiveTypeCode.SByte or PrimitiveTypeCode.Byte or PrimitiveTypeCode.Int16 or PrimitiveTypeCode.UInt16
                or PrimitiveTypeCode.Int32 or PrimitiveTypeCode.UInt32 or PrimitiveTypeCode.Int64 or PrimitiveTypeCode.UInt64
                => new("integer", typeCode.ToString()),
            PrimitiveTypeCode.Single or PrimitiveTypeCode.Double => new("number", typeCode.ToString()),
            PrimitiveTypeCode.String => new("string", "String"),
            PrimitiveTypeCode.Object => new("any", "Object"),
            PrimitiveTypeCode.Void => new("void", "Void"),
            _ => new(typeCode.ToString(), typeCode.ToString()),
        };

        public SigTypeInfo GetTypeFromDefinition(MetadataReader reader, TypeDefinitionHandle handle, byte rawTypeKind)
        {
            var name = reader.GetString(reader.GetTypeDefinition(handle).Name);
            return new(name, name);
        }

        public SigTypeInfo GetTypeFromReference(MetadataReader reader, TypeReferenceHandle handle, byte rawTypeKind)
        {
            var name = reader.GetString(reader.GetTypeReference(handle).Name);
            return new(name, name);
        }

        public SigTypeInfo GetTypeFromSpecification(MetadataReader reader, object? genericContext, TypeSpecificationHandle handle, byte rawTypeKind)
        {
            return reader.GetTypeSpecification(handle).DecodeSignature(this, genericContext);
        }

        public SigTypeInfo GetSZArrayType(SigTypeInfo elementType) =>
            new($"list<{elementType.FriendlyName}>", elementType.RawTypeName + "[]");

        public SigTypeInfo GetArrayType(SigTypeInfo elementType, ArrayShape shape) =>
            new($"list<{elementType.FriendlyName}>", elementType.RawTypeName + "[]");

        public SigTypeInfo GetGenericInstantiation(SigTypeInfo genericType, ImmutableArray<SigTypeInfo> typeArguments)
        {
            var raw = genericType.RawTypeName;
            var tick = raw.IndexOf('`');
            var clean = tick >= 0 ? raw[..tick] : raw;
            if (clean is "List" or "IList" or "IEnumerable" or "IReadOnlyList" or "ICollection" && typeArguments.Length == 1)
                return new($"list<{typeArguments[0].FriendlyName}>", raw);
            if (clean == "Nullable" && typeArguments.Length == 1)
                return typeArguments[0];
            return new($"{clean}<{string.Join(", ", typeArguments.Select(a => a.FriendlyName))}>", raw);
        }

        public SigTypeInfo GetByReferenceType(SigTypeInfo elementType) => elementType;
        public SigTypeInfo GetPinnedType(SigTypeInfo elementType) => elementType;
        public SigTypeInfo GetPointerType(SigTypeInfo elementType) => elementType;
        public SigTypeInfo GetModifiedType(SigTypeInfo modifier, SigTypeInfo unmodifiedType, bool isRequired) => unmodifiedType;
        public SigTypeInfo GetGenericMethodParameter(object? genericContext, int index) => new($"T{index}", $"T{index}");
        public SigTypeInfo GetGenericTypeParameter(object? genericContext, int index) => new($"T{index}", $"T{index}");
        public SigTypeInfo GetFunctionPointerType(MethodSignature<SigTypeInfo> signature) => new("Delegate", "Delegate");
    }

    private Dictionary<string, object?> DescribeOne(Type t, bool includeAdvanced)
    {
        var epdocType = _runtime.ResolveEpdocType(t);
        var fsType = _runtime.ResolveFieldSetType(t);
        var fsInst = fsType != null ? _runtime.GetFieldSetInstance(fsType) : null;

        string? ownerNote = null;
        if (fsType != null && fsInst != null)
        {
            ownerNote = fsType.GetProperty("OwnerEpNote")?.GetValue(fsInst)?.ToString()?.Trim();
        }
        var summary = !string.IsNullOrWhiteSpace(ownerNote)
            ? ownerNote!
            : (BridgeRuntime.GetEpdocNote(epdocType) ?? $"{t.Name} ({t.BaseType?.Name})");

        bool instantiable = !t.IsAbstract && !ExcludedClassNames.Contains(t.Name);

        var constructors = t.GetConstructors(BindingFlags.Public | BindingFlags.Instance)
            .Where(c => !c.GetParameters().Any(p => typeof(Delegate).IsAssignableFrom(p.ParameterType)))
            .Select(c => new Dictionary<string, object?>
            {
                ["parameters"] = c.GetParameters().Select(p => new Dictionary<string, object?>
                {
                    ["name"] = p.Name,
                    ["type"] = FriendlyTypeName(p.ParameterType),
                    ["required"] = !p.HasDefaultValue,
                    ["default"] = p.HasDefaultValue ? SafeDefault(p.DefaultValue) : null,
                }).ToList(),
            })
            .ToList();

        var wiringMethods = new List<Dictionary<string, object?>>();
        var seenWiring = new HashSet<string>(StringComparer.Ordinal);
        foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.Instance))
        {
            if (m.IsSpecialName) continue;
            if (m.DeclaringType == typeof(object)) continue;
            if (m.DeclaringType?.Name is "IB_ModelObject" or "IB_HVACObject") continue;
            if (BasePlumbingMethods.Contains(m.Name) || m.Name.StartsWith("ShouldSerialize", StringComparison.Ordinal) || m.Name.StartsWith("ToOS", StringComparison.Ordinal))
                continue;
            if (!(m.Name.StartsWith("Set", StringComparison.Ordinal) || m.Name.StartsWith("Add", StringComparison.Ordinal)))
                continue;
            var key = m.Name + "(" + string.Join(",", m.GetParameters().Select(p => p.ParameterType.Name)) + ")";
            if (!seenWiring.Add(key)) continue;
            wiringMethods.Add(new Dictionary<string, object?>
            {
                ["method"] = m.Name,
                ["slot_alias"] = ToSnakeCase(m.Name[3..]),
                ["parameters"] = m.GetParameters().Select(p => new Dictionary<string, object?>
                {
                    ["name"] = p.Name,
                    ["type"] = FriendlyTypeName(p.ParameterType),
                }).ToList(),
            });
        }

        var coreFields = new List<Dictionary<string, object?>>();
        var advancedFields = new List<Dictionary<string, object?>>();
        var coreNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        if (fsType != null && fsInst != null)
        {
            foreach (var p in fsType.GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly))
            {
                if (p.Name is "OwnerEpNote" or "Count" or "IsReadOnly") continue;
                var val = p.GetValue(fsInst);
                if (val == null) continue;
                var info = ExtractFieldInfo(val, epdocType);
                var fullName = info["name"]?.ToString() ?? p.Name;
                coreNames.Add(fullName);
                coreFields.Add(info);
            }

            if (fsInst is IEnumerable enumerable)
            {
                foreach (var item in enumerable)
                {
                    if (item == null) continue;
                    var info = ExtractFieldInfo(item, epdocType);
                    var fullName = info["name"]?.ToString() ?? "";
                    if (string.IsNullOrEmpty(fullName) || coreNames.Contains(fullName)) continue;
                    advancedFields.Add(info);
                }
            }
        }

        var result = new Dictionary<string, object?>
        {
            ["type_name"] = t.Name,
            ["instantiable"] = instantiable,
            ["category"] = Categorize(t),
            ["base_type"] = t.BaseType?.Name,
            ["summary"] = Truncate(summary, 800),
            ["constructors"] = constructors,
            ["wiring_methods"] = wiringMethods,
            ["core_fields"] = coreFields,
            ["advanced_field_count"] = advancedFields.Count,
        };
        if (!instantiable)
        {
            result["concrete_subclasses"] = EnumerateCatalogTypes()
                .Where(c => t.IsAssignableFrom(c))
                .Select(c => c.Name)
                .Take(25)
                .ToList();
        }
        if (includeAdvanced)
        {
            result["advanced_fields"] = advancedFields;
        }
        return result;
    }

    private Dictionary<string, object?> ExtractFieldInfo(object ibField, Type? epdocType)
    {
        var ft = ibField.GetType();
        var fullName = ft.GetProperty("FullName")?.GetValue(ibField)?.ToString() ?? "";
        var nickName = ft.GetProperty("NickName")?.GetValue(ibField)?.ToString();
        var dataTypeObj = ft.GetProperty("DataType")?.GetValue(ibField) as Type;
        var unit = ft.GetProperty("Unit")?.GetValue(ibField)?.ToString();
        var detailedDesc = ft.GetProperty("DetailedDescription")?.GetValue(ibField)?.ToString();

        var validDataObj = ft.GetProperty("ValidData")?.GetValue(ibField) as IEnumerable;
        var choices = new List<string>();
        if (validDataObj != null)
        {
            foreach (var v in validDataObj)
            {
                if (v != null)
                {
                    var s = v.ToString()?.Trim();
                    if (!string.IsNullOrEmpty(s)) choices.Add(s);
                }
            }
        }

        var epDesc = BridgeRuntime.GetEpdocFieldDescription(epdocType, fullName);
        var desc = !string.IsNullOrWhiteSpace(epDesc) ? epDesc! : (detailedDesc ?? "");
        var normalizedUnit = !string.IsNullOrWhiteSpace(unit) ? unit!.Trim() : ExtractUnitFromText(desc);
        var defaultVal = ExtractDefaultFromText(desc);

        var dict = new Dictionary<string, object?>
        {
            ["name"] = fullName,
            ["type"] = FriendlyTypeName(dataTypeObj),
        };
        if (!string.IsNullOrWhiteSpace(nickName) && !string.Equals(nickName, fullName, StringComparison.OrdinalIgnoreCase))
            dict["nick_name"] = nickName;
        if (!string.IsNullOrWhiteSpace(normalizedUnit))
            dict["unit"] = normalizedUnit;
        if (!string.IsNullOrWhiteSpace(defaultVal))
            dict["default"] = defaultVal;
        if (choices.Count > 0)
            dict["choices"] = choices;
        if (!string.IsNullOrWhiteSpace(desc))
            dict["description"] = Truncate(desc.Replace("\r", " ").Replace("\n", " "), 500);
        return dict;
    }

    private static string? ExtractUnitFromText(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return null;
        var bracketMatch = Regex.Match(text, @"\[(W/K|W/m2-K|W/m2|m3/sec|m3/s|kg/s|J/kg|°C|C|K|W|Pa|fraction|percent|%|kW|W/W|hr|hrs|sec|s)\]", RegexOptions.IgnoreCase);
        if (bracketMatch.Success)
        {
            return NormalizeUnitToken(bracketMatch.Groups[1].Value);
        }
        var phraseMatch = Regex.Match(text, @"(?i)\bin\s+(watts|W/K|W/m2|m3/sec|m3/s|Pa|degrees\s*C|°C|C|kg/s|K|W|fraction)\b");
        if (phraseMatch.Success)
        {
            return NormalizeUnitToken(phraseMatch.Groups[1].Value);
        }
        return null;
    }

    private static string NormalizeUnitToken(string raw)
    {
        var compact = Regex.Replace(raw.Trim(), @"\s+", " ").ToLowerInvariant();
        return compact switch
        {
            "watts" => "W",
            "degrees c" or "°c" => "C",
            "m3/sec" => "m3/s",
            _ => raw.Trim(),
        };
    }

    private static string? ExtractDefaultFromText(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return null;
        var m = Regex.Match(text, @"(?i)\b(?:the\s+)?(?:default(?:\s+value)?\s+(?:is|of)|defaults\s+to)\s+([A-Za-z0-9_+-]+(?:\.[A-Za-z0-9_+-]+)*)");
        return m.Success ? m.Groups[1].Value.Trim() : null;
    }

    private string GetTypeSummary(Type t)
    {
        var fsType = _runtime.ResolveFieldSetType(t);
        if (fsType != null)
        {
            var fsInst = _runtime.GetFieldSetInstance(fsType);
            var ownerNote = fsInst != null ? fsType.GetProperty("OwnerEpNote")?.GetValue(fsInst)?.ToString()?.Trim() : null;
            if (!string.IsNullOrWhiteSpace(ownerNote))
                return ownerNote!;
        }
        var epdocType = _runtime.ResolveEpdocType(t);
        return BridgeRuntime.GetEpdocNote(epdocType) ?? $"{t.Name} ({t.BaseType?.Name})";
    }

    public static string FriendlyTypeName(Type? t)
    {
        if (t == null) return "any";
        var underlying = Nullable.GetUnderlyingType(t);
        if (underlying != null) t = underlying;
        if (t == typeof(double) || t == typeof(float)) return "number";
        if (t == typeof(int) || t == typeof(long)) return "integer";
        if (t == typeof(bool)) return "boolean";
        if (t == typeof(string)) return "string";
        if (t.IsGenericType && t.GetGenericTypeDefinition() == typeof(List<>))
            return $"list<{FriendlyTypeName(t.GetGenericArguments()[0])}>";
        if (t.IsArray)
            return $"list<{FriendlyTypeName(t.GetElementType())}>";
        return t.Name;
    }

    private static object? SafeDefault(object? val)
    {
        if (val == null || val == DBNull.Value) return null;
        if (val.GetType().IsEnum) return val.ToString();
        return val;
    }

    private static string Truncate(string text, int maxLen)
    {
        var compact = string.Join(" ", text.Split(default(char[]), StringSplitOptions.RemoveEmptyEntries));
        if (compact.Length <= maxLen) return compact;
        return compact[..(maxLen - 3)] + "...";
    }

    internal static string ToSnakeCase(string text)
    {
        if (string.IsNullOrEmpty(text)) return text;
        var sb = new System.Text.StringBuilder();
        for (int i = 0; i < text.Length; i++)
        {
            var c = text[i];
            if (char.IsUpper(c) && i > 0 && (char.IsLower(text[i - 1]) || (i + 1 < text.Length && char.IsLower(text[i + 1]))))
                sb.Append('_');
            sb.Append(char.ToLowerInvariant(c));
        }
        return sb.ToString();
    }
}
