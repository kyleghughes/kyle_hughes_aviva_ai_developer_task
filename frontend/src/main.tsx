import React from "react";
import { createRoot } from "react-dom/client";
import Root from "./root";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
