import { Routes, Route } from "react-router";

import HomePage from "./pages/HomePage";
import MainLayout from "./layouts/MainLayout";

function App() {
  return (
    <Routes>
        <Route element={ <MainLayout/> }>
          <Route path="/" element={<HomePage />} />;
          <Route path="/analize-image" element={<HomePage />} />;
          <Route path="/result-image" element={<HomePage />} />;
          <Route path="/galery" element={<HomePage />} />;
          <Route path="/progress" element={<HomePage />} />;
          <Route path="/exercise" element={<HomePage />} />;
          <Route path="/profile" element={<HomePage />} />;
        </Route>
    </Routes>
  );
}

export default App;
