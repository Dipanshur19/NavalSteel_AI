let ready;
async function initialize() {
  importScripts("runtime/pyodide.js");
  const runtime = await loadPyodide({
    indexURL: new URL("runtime/", self.location.href).href,
  });
  const response = await fetch("engine.zip");
  if (!response.ok) throw Error("The analysis files could not be loaded.");
  runtime.FS.mkdir("/workspace");
  runtime.unpackArchive(await response.arrayBuffer(), "zip", {
    extractDir: "/workspace",
  });
  runtime.runPython(
    "import sys, json\nsys.path.insert(0, '/workspace')\nfrom src.browser_engine import dispatch",
  );
  return runtime;
}
self.onmessage = async ({ data }) => {
  try {
    if (!ready)
      ready = initialize().catch((error) => {
        ready = null;
        throw error;
      });
    const runtime = await ready;
    runtime.globals.set("action", data.action);
    runtime.globals.set("payload", JSON.stringify(data.payload));
    const result = runtime.runPython(
      "json.dumps(dispatch(action,json.loads(payload)), allow_nan=False)",
    );
    self.postMessage({ id: data.id, result: JSON.parse(result) });
  } catch (error) {
    console.error(error);
    self.postMessage({
      id: data.id,
      error: "Analysis could not finish. Check the inputs and retry.",
    });
  }
};
