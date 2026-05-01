import React from "react";
import ReactDOM from "react-dom/client";
import "./app/index.css";
import { Providers } from "./app/providers";
import { AppRoutes } from "./app/routes";

const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);

root.render(
  <React.StrictMode>
    <Providers>
      <AppRoutes />
    </Providers>
  </React.StrictMode>
);
