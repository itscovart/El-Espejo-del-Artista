import { useEffect, useState } from "react";
import { Routes, Route, Navigate, Outlet, useNavigate } from "react-router-dom";

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
import AdminUser from "./pages/AdminUser";
import { BACKEND_API_URL } from "./config/api";

export type User = {
  id_user: number;
  first_name: string;
  middle_name: string;
  last_name: string;
  email: string;
  register_date: string;
  type: string;
};

// TODO: Información que guardar por obra y pasara como parametro a la vistas
export type WorkInfo = {
  id_image: number;
  image_title: string;
  image_url: string;
  image_date: string;
};

// TODO: Información del análisis que recibe el front
export type WorkAnalisis = {};

function ProtectedRouteUser({ user }) {
  if (!user) {
    return <Navigate to="/access" replace />;
  }

  return <Outlet />;
}

function ProtectedRouteAdmin({ user }) {
  if (user.type === "Administrador") {
    return <Outlet />;
  }
  return <Navigate to="/profile" replace />;
}

function NonProtectedRouteUser({ user }) {
  if (user === null) {
    return <Navigate to="/access" replace />;
  } else {
    return <Navigate to="/" replace />;
  }
}

const verificarSesion = async (setUser) => {
  try {
    let response = await fetch(`${BACKEND_API_URL}/auth/me`, {
      method: "GET",
      credentials: "include",
    });

    // Si el access token expiró, intentamos renovarlo
    if (response.status === 401) {
      const refresh = await fetch(`${BACKEND_API_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });

      if (!refresh.ok) {
        throw new Error("Sesión expirada");
      }

      // Volvemos a consultar al usuario
      response = await fetch(`${BACKEND_API_URL}/auth/me`, {
        method: "GET",
        credentials: "include",
      });
    }

    if (!response.ok) {
      throw new Error("No se pudo recuperar la sesión");
    }

    const usuario = await response.json();

    setUser(usuario);
  } catch (error) {
    setUser(null);
  }
};

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [dataAnalisis, setDataAnalisis] = useState(null);
  const [gallery, setGallery] = useState(null);

  useEffect(() => {
    const iniciarSesion = async () => {
      try {
        await verificarSesion(setUser);
      } finally {
        setLoading(false);
      }
    };

    iniciarSesion();
  }, []);

  if (loading) {
    return <div>Verificando sesión...</div>;
  }
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route element={<ProtectedRouteUser user={user} />}>
          <Route element={<ProtectedRouteAdmin user={user} />}>
            <Route path="/users-panel" element={<AdminUser />} />
          </Route>
          <Route path="/" element={<HomePage user={user} />} />
          <Route
            path="/analize-image"
            element={<AnalizeImgPage user={user} />}
          />
          <Route path="/result-image" element={<ResultPage data={dataAnalisis} setData={setDataAnalisis} />} />
          <Route path="/gallery" element={<GalleryPage user={user} data={gallery} setData={setGallery}/>} />
          <Route path="/progress" element={<ProgressPage />} />
          <Route path="/exercise" element={<ExercisePage />} />
          <Route
            path="/profile"
            element={<ProfilePage user={user} setUser={setUser} />}
          />
          <Route path="/resources" element={<ResourcesPage />} />
        </Route>

        <Route element={<NonProtectedRouteUser user={user} />}>
          <Route path="/access" element={<AccessPage setUser={setUser} />} />
        </Route>
      </Route>
    </Routes>
  );
}

export default App;
