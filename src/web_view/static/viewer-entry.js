import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "@kitware/vtk.js/Rendering/Profiles/Geometry";
import "@kitware/vtk.js/IO/Core/DataAccessHelper/JSZipDataAccessHelper";
import DataAccessHelper from "@kitware/vtk.js/IO/Core/DataAccessHelper";
import vtkHttpSceneLoader from "@kitware/vtk.js/IO/Core/HttpSceneLoader";
import vtkGenericRenderWindow from "@kitware/vtk.js/Rendering/Misc/GenericRenderWindow";

const boundsCenter = (bounds) => [
  (bounds[0] + bounds[1]) / 2,
  (bounds[2] + bounds[3]) / 2,
  (bounds[4] + bounds[5]) / 2,
];

const boundsRadius = (bounds) => {
  const dx = bounds[1] - bounds[0];
  const dy = bounds[3] - bounds[2];
  const dz = bounds[5] - bounds[4];
  return Math.max(dx, dy, dz) || 1;
};

const setCamera = ({ renderer, renderWindow, center, radius }, mode) => {
  const camera = renderer.getActiveCamera();
  const position =
    mode === "top"
      ? [center[0], center[1], center[2] + radius * 1.45]
      : [center[0] + radius * 1.1, center[1] - radius * 1.0, center[2] + radius * 0.72];
  const viewUp = mode === "top" ? [0, 1, 0] : [0, 0, 1];

  camera.setFocalPoint(center[0], center[1], center[2]);
  camera.setPosition(position[0], position[1], position[2]);
  camera.setViewUp(viewUp[0], viewUp[1], viewUp[2]);
  camera.setClippingRange(0.01, radius * 10);
  renderer.resetCameraClippingRange();
  renderWindow.render();
};

const withRevision = (path, revision) => {
  if (!revision) {
    return path;
  }
  const joiner = path.includes("?") ? "&" : "?";
  return `${path}${joiner}v=${encodeURIComponent(revision)}`;
};

const loadJson = async (path) => {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load ${path}.`);
  }
  return response.json();
};

const loadConfig = () => loadJson(`./config.json?t=${Date.now()}`);

const VtkjsViewer = () => {
  const containerRef = useRef(null);
  const contextRef = useRef(null);
  const [config, setConfig] = useState(null);
  const [hbModel, setHbModel] = useState(null);
  const [status, setStatus] = useState("Loading config");
  const [error, setError] = useState(null);

  useEffect(() => {
    let disposed = false;
    let lastConfigText = "";

    const applyConfig = (nextConfig) => {
      const nextConfigText = JSON.stringify(nextConfig);
      if (nextConfigText === lastConfigText) {
        return;
      }
      lastConfigText = nextConfigText;
      setConfig(nextConfig);
      document.title = nextConfig.title;
      setStatus(`Ready ${nextConfig.revision?.slice(0, 8) ?? ""}`.trim());
    };

    const refresh = async () => {
      try {
        const nextConfig = await loadConfig();
        if (!disposed) {
          applyConfig(nextConfig);
        }
      } catch (reason) {
        if (!disposed) {
          setError(reason instanceof Error ? reason.message : String(reason));
          setStatus("Failed");
        }
      }
    };

    refresh();
    const interval = window.setInterval(refresh, 1500);
    return () => {
      disposed = true;
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (!config?.model?.path) {
      setHbModel(null);
      return undefined;
    }

    let disposed = false;
    loadJson(withRevision(config.model.path, config.revision))
      .then((model) => {
        if (!disposed) {
          setHbModel(model);
        }
      })
      .catch(() => {
        if (!disposed) {
          setHbModel(null);
        }
      });

    return () => {
      disposed = true;
    };
  }, [config?.model?.path, config?.revision]);

  useEffect(() => {
    const activeArtifact = config?.artifact ?? null;
    if (!activeArtifact || !containerRef.current) {
      return undefined;
    }

    let disposed = false;
    const loadScene = async () => {
      contextRef.current?.genericRenderWindow.delete();
      contextRef.current = null;
      setStatus(`Loading ${activeArtifact.name}`);
      setError(null);

      const artifactResponse = await fetch(withRevision(activeArtifact.path, config.revision), {
        cache: "no-store",
      });
      if (!artifactResponse.ok) {
        throw new Error(`Failed to load ${activeArtifact.path}.`);
      }

      const zipContent = await artifactResponse.arrayBuffer();
      const genericRenderWindow = vtkGenericRenderWindow.newInstance({
        background: [0.96, 0.95, 0.91],
        listenWindowResize: true,
      });
      genericRenderWindow.setContainer(containerRef.current);
      genericRenderWindow.resize();

      const renderer = genericRenderWindow.getRenderer();
      const renderWindow = genericRenderWindow.getRenderWindow();
      const dataAccessHelper = DataAccessHelper.get("zip", {
        zipContent,
        callback: () => {
          const sceneImporter = vtkHttpSceneLoader.newInstance({
            renderer,
            dataAccessHelper,
          });

          sceneImporter.onReady(() => {
            if (disposed) {
              genericRenderWindow.delete();
              return;
            }

            const bounds = renderer.computeVisiblePropBounds();
            const center = boundsCenter(bounds);
            const radius = boundsRadius(bounds) * 2.7;

            contextRef.current = {
              genericRenderWindow,
              renderer,
              renderWindow,
              center,
              radius,
            };
            setCamera(contextRef.current, "axon");
            setStatus(`Loaded ${activeArtifact.name}`);
          });

          sceneImporter.setUrl("index.json");
        },
      });
    };

    loadScene().catch((reason) => {
      setError(reason instanceof Error ? reason.message : String(reason));
      setStatus("Failed");
    });

    return () => {
      disposed = true;
      contextRef.current?.genericRenderWindow.delete();
      contextRef.current = null;
    };
  }, [config?.artifact?.path, config?.revision]);

  const view = (cameraMode) => {
    if (contextRef.current) {
      setCamera(contextRef.current, cameraMode);
    }
  };

  const roomCount = hbModel?.rooms?.length ?? null;

  return React.createElement(
    "main",
    { className: "page" },
    React.createElement(
      "header",
      { className: "toolbar" },
      React.createElement(
        "div",
        { className: "titleBlock" },
        React.createElement("h1", null, config?.title ?? "Ladybug Tools Web View"),
        React.createElement(
          "p",
          null,
          [
            status,
            hbModel?.display_name ?? hbModel?.identifier,
            Number.isInteger(roomCount) ? `${roomCount} rooms` : null,
          ]
            .filter(Boolean)
            .join(" | "),
        ),
      ),
      React.createElement(
        "div",
        { className: "buttons" },
        React.createElement("button", { type: "button", onClick: () => view("axon") }, "Axon"),
        React.createElement("button", { type: "button", onClick: () => view("top") }, "Top"),
      ),
    ),
    React.createElement(
      "section",
      { className: "workspace" },
      React.createElement("div", { ref: containerRef, className: "viewer" }),
    ),
    error ? React.createElement("pre", { className: "error" }, error) : null,
    React.createElement("style", null, `
      .page {
        width: 100%;
        height: 100%;
        display: grid;
        grid-template-rows: 64px 1fr;
        color: #1d2528;
      }

      .toolbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 10px 14px;
        border-bottom: 1px solid rgba(29, 37, 40, 0.14);
        background: rgba(255, 255, 255, 0.92);
      }

      h1, p {
        margin: 0;
      }

      h1 {
        font-size: 16px;
        font-weight: 680;
      }

      .titleBlock p {
        margin-top: 3px;
        font-size: 12px;
        color: #5b6568;
      }

      .buttons {
        display: flex;
        gap: 8px;
      }

      button {
        min-height: 34px;
        padding: 0 12px;
        border: 1px solid rgba(29, 37, 40, 0.18);
        background: #ffffff;
        color: #1d2528;
        cursor: pointer;
      }

      .workspace {
        min-height: 0;
      }

      .viewer {
        position: relative;
        min-height: 0;
        width: 100%;
        height: 100%;
      }

      .viewer canvas {
        display: block;
      }

      .error {
        position: absolute;
        left: 16px;
        right: 16px;
        bottom: 16px;
        margin: 0;
        padding: 12px;
        white-space: pre-wrap;
        background: #fff2f0;
        color: #9a1f12;
        border: 1px solid #ffc9c2;
      }

      @media (max-width: 760px) {
        .page {
          grid-template-rows: auto 1fr;
        }

        .toolbar {
          align-items: flex-start;
          flex-direction: column;
        }
      }
    `),
  );
};

createRoot(document.getElementById("root")).render(React.createElement(VtkjsViewer));
