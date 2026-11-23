using System.Text;
using System.Text.Json;

namespace IronbugBridge;

internal static class Program
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = null,
        WriteIndented = false,
    };

    public static int Main(string[] args)
    {
        // Save real stdout for JSON Lines protocol and redirect Console.Out to stderr
        // so OpenStudio / Ironbug console prints never corrupt stdout RPC frames.
        var originalOut = Console.OpenStandardOutput();
        var protocolOut = new StreamWriter(originalOut, new UTF8Encoding(false)) { AutoFlush = true };
        Console.SetOut(Console.Error);

        string? ironbugDir = null;
        string? openStudioCSharpDir = null;
        bool serve = false;
        string? oneShotCommand = null;
        string? payloadFile = null;

        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--ironbug-dir" when i + 1 < args.Length:
                    ironbugDir = args[++i];
                    break;
                case "--openstudio-csharp-dir" when i + 1 < args.Length:
                    openStudioCSharpDir = args[++i];
                    break;
                case "--serve":
                    serve = true;
                    break;
                case "--command" when i + 1 < args.Length:
                    oneShotCommand = args[++i];
                    break;
                case "--payload-file" when i + 1 < args.Length:
                    payloadFile = args[++i];
                    break;
            }
        }

        if (string.IsNullOrWhiteSpace(ironbugDir))
        {
            WriteErrorResponse(protocolOut, "init", "ArgumentException", "--ironbug-dir is required.");
            return 2;
        }

        BridgeRuntime runtime;
        try
        {
            runtime = new BridgeRuntime(ironbugDir, openStudioCSharpDir);
        }
        catch (Exception ex)
        {
            WriteErrorResponse(protocolOut, "init", ex.GetType().Name, ex.Message);
            return 1;
        }

        var inspector = new CatalogInspector(runtime);
        var builder = new SystemBuilder(runtime);

        if (!string.IsNullOrWhiteSpace(oneShotCommand))
        {
            JsonElement? payload = null;
            if (!string.IsNullOrWhiteSpace(payloadFile))
            {
                var raw = File.ReadAllText(payloadFile, Encoding.UTF8);
                payload = JsonDocument.Parse(raw).RootElement.Clone();
            }
            else if (!Console.IsInputRedirected)
            {
                payload = JsonDocument.Parse("{}").RootElement.Clone();
            }
            else
            {
                var stdinText = Console.In.ReadToEnd();
                payload = string.IsNullOrWhiteSpace(stdinText)
                    ? JsonDocument.Parse("{}").RootElement.Clone()
                    : JsonDocument.Parse(stdinText).RootElement.Clone();
            }

            HandleAndWrite(protocolOut, "oneshot", oneShotCommand, payload.Value, runtime, inspector, builder);
            return 0;
        }

        if (serve)
        {
            using var reader = new StreamReader(Console.OpenStandardInput(), new UTF8Encoding(false));
            string? line;
            while ((line = reader.ReadLine()) != null)
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                string reqId = "";
                try
                {
                    using var doc = JsonDocument.Parse(line);
                    var root = doc.RootElement;
                    reqId = root.TryGetProperty("id", out var idEl) ? (idEl.GetString() ?? "") : "";
                    var method = root.TryGetProperty("method", out var mEl) ? (mEl.GetString() ?? "") : "";
                    var paramEl = root.TryGetProperty("params", out var pEl)
                        ? pEl
                        : JsonDocument.Parse("{}").RootElement;
                    HandleAndWrite(protocolOut, reqId, method, paramEl, runtime, inspector, builder);
                }
                catch (Exception ex)
                {
                    WriteErrorResponse(protocolOut, reqId, ex.GetType().Name, ex.Message);
                }
            }
            return 0;
        }

        // Default: print health JSON once
        HandleAndWrite(protocolOut, "health", "health", JsonDocument.Parse("{}").RootElement, runtime, inspector, builder);
        return 0;
    }

    private static void HandleAndWrite(
        TextWriter protocolOut,
        string reqId,
        string method,
        JsonElement paramsEl,
        BridgeRuntime runtime,
        CatalogInspector inspector,
        SystemBuilder builder)
    {
        try
        {
            object? result = method switch
            {
                "health" => runtime.Health(),
                "catalog" => HandleCatalog(inspector, paramsEl),
                "describe" => HandleDescribe(inspector, paramsEl),
                "build" => builder.Build(paramsEl),
                "validate" => HandleValidate(builder, paramsEl),
                "inspect" => HandleInspect(builder, paramsEl),
                _ => throw new InvalidOperationException($"Unsupported bridge method: {method}"),
            };

            var envelope = new Dictionary<string, object?>
            {
                ["id"] = reqId,
                ["ok"] = true,
                ["result"] = result,
            };
            protocolOut.WriteLine(JsonSerializer.Serialize(envelope, JsonOptions));
        }
        catch (Exception ex)
        {
            var inner = ex is System.Reflection.TargetInvocationException tie && tie.InnerException != null
                ? tie.InnerException
                : ex;
            WriteErrorResponse(protocolOut, reqId, inner.GetType().Name, inner.Message);
        }
    }

    private static object HandleCatalog(CatalogInspector inspector, JsonElement p)
    {
        string? category = p.TryGetProperty("category", out var cEl) && cEl.ValueKind == JsonValueKind.String
            ? cEl.GetString()
            : null;
        string? query = p.TryGetProperty("query", out var qEl) && qEl.ValueKind == JsonValueKind.String
            ? qEl.GetString()
            : null;
        int limit = p.TryGetProperty("limit", out var lEl) && lEl.ValueKind == JsonValueKind.Number
            ? lEl.GetInt32()
            : 25;
        int offset = p.TryGetProperty("offset", out var oEl) && oEl.ValueKind == JsonValueKind.Number
            ? Math.Max(0, oEl.GetInt32())
            : 0;
        return inspector.Catalog(category, query, limit, offset);
    }

    private static object HandleDescribe(CatalogInspector inspector, JsonElement p)
    {
        var typeNames = new List<string>();
        if (p.TryGetProperty("type_names", out var listEl) && listEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in listEl.EnumerateArray())
            {
                if (item.ValueKind == JsonValueKind.String && item.GetString() is string s && !string.IsNullOrWhiteSpace(s))
                {
                    typeNames.Add(s);
                }
            }
        }
        else if (p.TryGetProperty("type_name", out var singleEl) && singleEl.ValueKind == JsonValueKind.String)
        {
            var s = singleEl.GetString();
            if (!string.IsNullOrWhiteSpace(s)) typeNames.Add(s);
        }
        bool includeAdvanced = p.TryGetProperty("include_advanced", out var advEl) && advEl.ValueKind == JsonValueKind.True;
        return inspector.Describe(typeNames, includeAdvanced);
    }

    private static object HandleValidate(SystemBuilder builder, JsonElement p)
    {
        var specJson = p.TryGetProperty("specification_json", out var sEl) && sEl.ValueKind == JsonValueKind.String
            ? sEl.GetString()!
            : (p.TryGetProperty("specification", out var objEl) ? objEl.GetRawText() : throw new ArgumentException("specification_json is required."));
        var roomNames = new List<string>();
        if (p.TryGetProperty("room_names", out var rEl) && rEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in rEl.EnumerateArray())
            {
                if (item.ValueKind == JsonValueKind.String && item.GetString() is string s && !string.IsNullOrWhiteSpace(s))
                {
                    roomNames.Add(s);
                }
            }
        }
        return builder.Validate(specJson, roomNames);
    }

    private static object HandleInspect(SystemBuilder builder, JsonElement p)
    {
        var specJson = p.TryGetProperty("specification_json", out var sEl) && sEl.ValueKind == JsonValueKind.String
            ? sEl.GetString()!
            : (p.TryGetProperty("specification", out var objEl) ? objEl.GetRawText() : throw new ArgumentException("specification_json is required."));
        return builder.Inspect(specJson);
    }

    private static void WriteErrorResponse(TextWriter protocolOut, string reqId, string errorType, string message)
    {
        var envelope = new Dictionary<string, object?>
        {
            ["id"] = reqId,
            ["ok"] = false,
            ["error"] = new Dictionary<string, object?>
            {
                ["type"] = errorType,
                ["message"] = message,
            },
        };
        protocolOut.WriteLine(JsonSerializer.Serialize(envelope, JsonOptions));
    }
}
