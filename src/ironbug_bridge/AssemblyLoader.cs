using System.Collections;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Runtime.Loader;

namespace IronbugBridge;

/// <summary>
/// Dynamically resolves external Ironbug.HVAC, Ironbug.EPDoc, and OpenStudio assemblies
/// from user-installed Ladybug Tools directories without hardcoding assembly versions.
/// </summary>
internal sealed class BridgeRuntime
{
    private readonly List<string> _probeDirectories = new();
    private readonly object _lock = new();
    private Assembly? _hvacAssembly;
    private Assembly? _epdocAssembly;
    private Assembly? _openStudioAssembly;
    private Dictionary<string, Type>? _hvacTypesByName;
    private Dictionary<string, Type>? _epdocTypesByName;
    private bool _resolverRegistered;

    public string IronbugDir { get; }
    public string? OpenStudioCSharpDir { get; }
    public string HvacAssemblyPath => Path.Combine(IronbugDir, "Ironbug.HVAC.dll");
    public bool HasOpenStudio => _probeDirectories.Any(dir => File.Exists(Path.Combine(dir, "OpenStudio.dll")));

    public BridgeRuntime(string ironbugDir, string? openStudioCSharpDir)
    {
        IronbugDir = Path.GetFullPath(ironbugDir);
        if (!Directory.Exists(IronbugDir))
        {
            throw new DirectoryNotFoundException($"Ironbug directory not found: {IronbugDir}");
        }
        _probeDirectories.Add(IronbugDir);

        if (!string.IsNullOrWhiteSpace(openStudioCSharpDir))
        {
            var fullOsDir = Path.GetFullPath(openStudioCSharpDir);
            if (Directory.Exists(fullOsDir))
            {
                OpenStudioCSharpDir = fullOsDir;
                if (!string.Equals(fullOsDir, IronbugDir, StringComparison.OrdinalIgnoreCase))
                {
                    _probeDirectories.Add(fullOsDir);
                }
            }
        }

        EnsureResolvers();
    }

    private void EnsureResolvers()
    {
        if (_resolverRegistered) return;
        _resolverRegistered = true;

        AssemblyLoadContext.Default.Resolving += (context, assemblyName) =>
        {
            var fileName = assemblyName.Name + ".dll";
            var baseCandidate = Path.Combine(AppContext.BaseDirectory, fileName);
            if (File.Exists(baseCandidate))
            {
                return context.LoadFromAssemblyPath(baseCandidate);
            }
            foreach (var dir in _probeDirectories)
            {
                var candidate = Path.Combine(dir, fileName);
                if (File.Exists(candidate))
                {
                    return context.LoadFromAssemblyPath(candidate);
                }
            }
            return null;
        };

        AssemblyLoadContext.Default.ResolvingUnmanagedDll += (_, unmanagedDllName) =>
        {
            foreach (var candidateName in UnmanagedCandidates(unmanagedDllName))
            {
                foreach (var dir in _probeDirectories)
                {
                    var fullPath = Path.Combine(dir, candidateName);
                    if (File.Exists(fullPath) && NativeLibrary.TryLoad(fullPath, out var handle))
                    {
                        return handle;
                    }
                }
            }
            return IntPtr.Zero;
        };
    }

    private static IEnumerable<string> UnmanagedCandidates(string name)
    {
        yield return name;
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            if (!name.EndsWith(".dll", StringComparison.OrdinalIgnoreCase))
                yield return name + ".dll";
        }
        else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
        {
            if (!name.EndsWith(".dylib", StringComparison.OrdinalIgnoreCase))
            {
                yield return name + ".dylib";
                yield return "lib" + name + ".dylib";
            }
        }
        else
        {
            if (!name.EndsWith(".so", StringComparison.OrdinalIgnoreCase))
            {
                yield return name + ".so";
                yield return "lib" + name + ".so";
            }
        }
    }

    public Assembly HvacAssembly
    {
        get
        {
            lock (_lock)
            {
                if (_hvacAssembly != null) return _hvacAssembly;
                var dllPath = Path.Combine(IronbugDir, "Ironbug.HVAC.dll");
                if (!File.Exists(dllPath))
                {
                    throw new FileNotFoundException($"Ironbug.HVAC.dll not found in {IronbugDir}", dllPath);
                }
                _hvacAssembly = AssemblyLoadContext.Default.LoadFromAssemblyPath(dllPath);
                return _hvacAssembly;
            }
        }
    }

    public Assembly? EpdocAssembly
    {
        get
        {
            lock (_lock)
            {
                if (_epdocAssembly != null) return _epdocAssembly;
                var dllPath = Path.Combine(IronbugDir, "Ironbug.EPDoc.dll");
                if (File.Exists(dllPath))
                {
                    _epdocAssembly = AssemblyLoadContext.Default.LoadFromAssemblyPath(dllPath);
                }
                return _epdocAssembly;
            }
        }
    }

    public Assembly OpenStudioAssembly
    {
        get
        {
            lock (_lock)
            {
                if (_openStudioAssembly != null) return _openStudioAssembly;
                foreach (var dir in _probeDirectories)
                {
                    var candidate = Path.Combine(dir, "OpenStudio.dll");
                    if (File.Exists(candidate))
                    {
                        _openStudioAssembly = AssemblyLoadContext.Default.LoadFromAssemblyPath(candidate);
                        return _openStudioAssembly;
                    }
                }
                throw new FileNotFoundException(
                    "OpenStudio.dll was not found in the configured Ironbug or OpenStudio CSharp directories."
                );
            }
        }
    }

    public Type[] GetAllHvacTypes()
    {
        try
        {
            return HvacAssembly.GetExportedTypes();
        }
        catch (ReflectionTypeLoadException rtle)
        {
            return rtle.Types.Where(t => t != null && t.IsPublic).ToArray()!;
        }
        catch (FileNotFoundException)
        {
            try
            {
                return HvacAssembly.GetTypes().Where(t => t.IsPublic).ToArray();
            }
            catch (ReflectionTypeLoadException rtle)
            {
                return rtle.Types.Where(t => t != null && t.IsPublic).ToArray()!;
            }
        }
    }

    public Dictionary<string, Type> HvacTypesByName
    {
        get
        {
            lock (_lock)
            {
                if (_hvacTypesByName != null) return _hvacTypesByName;
                var map = new Dictionary<string, Type>(StringComparer.OrdinalIgnoreCase);
                foreach (var t in GetAllHvacTypes())
                {
                    map.TryAdd(t.Name, t);
                    if (t.FullName != null) map.TryAdd(t.FullName, t);
                }
                _hvacTypesByName = map;
                return map;
            }
        }
    }

    public Dictionary<string, Type> EpdocTypesByName
    {
        get
        {
            lock (_lock)
            {
                if (_epdocTypesByName != null) return _epdocTypesByName;
                var map = new Dictionary<string, Type>(StringComparer.OrdinalIgnoreCase);
                var asm = EpdocAssembly;
                if (asm != null)
                {
                    foreach (var t in asm.GetExportedTypes())
                    {
                        map.TryAdd(t.Name, t);
                    }
                }
                _epdocTypesByName = map;
                return map;
            }
        }
    }

    public Type ResolveHvacType(string typeName)
    {
        if (HvacTypesByName.TryGetValue(typeName, out var exact))
        {
            return exact;
        }
        if (!typeName.StartsWith("IB_", StringComparison.OrdinalIgnoreCase))
        {
            if (HvacTypesByName.TryGetValue("IB_" + typeName, out var prefixed))
            {
                return prefixed;
            }
        }
        throw new KeyNotFoundException($"Unknown Ironbug type: {typeName}");
    }

    public Type? ResolveFieldSetType(Type ibType)
    {
        if (HvacTypesByName.TryGetValue(ibType.Name + "_FieldSet", out var direct))
        {
            return direct;
        }
        if (ibType.FullName != null && HvacTypesByName.TryGetValue(ibType.FullName + "_FieldSet", out var full))
        {
            return full;
        }
        return null;
    }

    public object? GetFieldSetInstance(Type fsType)
    {
        var valProp = fsType.GetProperty("Value", BindingFlags.Public | BindingFlags.Static | BindingFlags.FlattenHierarchy);
        if (valProp != null)
        {
            return valProp.GetValue(null);
        }
        try
        {
            return Activator.CreateInstance(fsType);
        }
        catch
        {
            return null;
        }
    }

    public Type? ResolveEpdocType(Type ibType)
    {
        return ResolveEpdocTypeByName(ibType.Name);
    }

    public Type? ResolveEpdocTypeByName(string ibTypeName)
    {
        var baseName = ibTypeName.StartsWith("IB_", StringComparison.OrdinalIgnoreCase)
            ? ibTypeName[3..]
            : ibTypeName;
        if (EpdocTypesByName.TryGetValue(baseName, out var t))
        {
            return t;
        }
        return null;
    }

    public static string? GetEpdocNote(Type? epdocType)
    {
        if (epdocType == null) return null;
        var field = epdocType.GetField("Note", BindingFlags.Public | BindingFlags.Static | BindingFlags.IgnoreCase);
        return field?.GetValue(null)?.ToString()?.Trim();
    }

    public static string? GetEpdocFieldDescription(Type? epdocType, string fullName)
    {
        if (epdocType == null || string.IsNullOrWhiteSpace(fullName)) return null;
        var candidate = "Field_" + fullName;
        var field = epdocType.GetField(candidate, BindingFlags.Public | BindingFlags.Static | BindingFlags.IgnoreCase);
        if (field != null) return field.GetValue(null)?.ToString()?.Trim();

        // Fallback: normalize punctuation if EPDoc sanitized field identifier
        var sanitized = "Field_" + new string(fullName.Where(char.IsLetterOrDigit).ToArray());
        foreach (var f in epdocType.GetFields(BindingFlags.Public | BindingFlags.Static))
        {
            if (string.Equals(f.Name, sanitized, StringComparison.OrdinalIgnoreCase))
            {
                return f.GetValue(null)?.ToString()?.Trim();
            }
        }
        return null;
    }

    public Dictionary<string, object?> Health()
    {
        var hvacVer = HvacAssembly.GetName().Version?.ToString() ?? "unknown";
        var epdocLoaded = EpdocAssembly != null;
        string? osVer = null;
        string? osError = null;
        try
        {
            osVer = OpenStudioAssembly.GetName().Version?.ToString();
        }
        catch (Exception ex)
        {
            osError = ex.Message;
        }

        var sysType = ResolveHvacType("IB_HVACSystem");
        var capabilities = new Dictionary<string, bool>
        {
            ["air_loops"] = sysType.GetProperty("AirLoops") != null,
            ["plant_loops"] = sysType.GetProperty("PlantLoops") != null,
            ["vrf_systems"] = sysType.GetProperty("VariableRefrigerantFlows") != null,
            ["energy_management_system"] = sysType.GetProperty("EnergyManagementSystem") != null,
            ["electric_load_center"] = sysType.GetProperty("ElectricLoadCenter") != null,
        };

        return new Dictionary<string, object?>
        {
            ["ok"] = true,
            ["ironbug_dir"] = IronbugDir,
            ["openstudio_csharp_dir"] = OpenStudioCSharpDir,
            ["ironbug_hvac_version"] = hvacVer,
            ["epdoc_loaded"] = epdocLoaded,
            ["openstudio_version"] = osVer,
            ["openstudio_error"] = osError,
            ["capabilities"] = capabilities,
        };
    }
}
