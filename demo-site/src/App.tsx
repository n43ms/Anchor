import React from "react";
import { LandingPage } from "./components/LandingPage";
import { DemoProvider } from "./context/DemoProvider";

export function App() {
  return (
    <DemoProvider>
      <LandingPage />
    </DemoProvider>
  );
}

export default App;

