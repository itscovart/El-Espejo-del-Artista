import { Routes, Route } from "react-router";

import HomePage from "./pages/HomePage";
import MainLayout from "./layouts/MainLayout";
import AnalizeImgPage from "./pages/AnalizeImgPage";
import AccessPage from "./pages/AccessPage";
import ExercisePage from "./pages/ExercisePage";
import GalleryPage from "./pages/GalleryPage";
import ProfilePage from "./pages/ProfilePage";
import ProgressPage from "./pages/ProgressPage";
import ResourcesPage from "./pages/ResourcesPage";
import ResultPage from "./pages/ResultPage";


function App() {
  return (
    <Routes>
        <Route element={ <MainLayout/> }>
          <Route path="/" element={<HomePage />} />;
          <Route path="/analize-image" element={<AnalizeImgPage/>} />;
          <Route path="/result-image" element={<ResultPage />} />;
          <Route path="/gallery" element={<GalleryPage />} />;
          <Route path="/progress" element={<ProgressPage />} />;
          <Route path="/exercise" element={<ExercisePage />} />;
          <Route path="/profile" element={<ProfilePage />} />;
        </Route>
    </Routes>
  );
}

export default App;
