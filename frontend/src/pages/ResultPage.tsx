import { useEffect } from "react";
import { BACKEND_API_URL } from "../config/api";
import {
  Artwork,
  Badge,
  DisplayDate,
  PageFrame,
  PageHeading,
  PageLink,
  Panel,
  SectionTitle,
} from "./HomePage";
import type { ArtworkData } from "./HomePage";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

// 04-resultado: datos ficticios de la obra de ejemplo, sin simular un análisis real.
export type ResultPageData = {
  artwork: ArtworkData;
  status: string;
  metrics: number[];
  palette: { name: string; hex_color: string }[];
  critique: string;
  exercise: { title: string; description: string; status: string };
};
export type ResultPageProps = { data?: ResultPageData };

/** API -> data: resultado del usuario autorizado. metrics es una tupla
 * [contraste, iluminación, balance] de 0 a 100; palette usa colores #RRGGBB;
 * artwork.date es ISO; exercise puede ser null. No se calcula un análisis aquí.
 */
export default function ResultPage({ data, setData }) {
  const [searchParams] = useSearchParams();
  const image_id = searchParams.get("image_id");
  const navigate = useNavigate();


  useEffect(() => {
    if (image_id === null || image_id === undefined) {
      alert("image_id nulo o indefinido");
      navigate("/");
      return;
    }
    const fetchAnalisis = async () => {
      const response = await fetch(
        `${BACKEND_API_URL}/works/analize-get?image_id=${image_id}`,
        { method: "GET", credentials: "include" },
      );
      if (response.ok) {
        const work = await response.json();
        setData(work);
      } else {
        navigate("/");
      }
    };

    fetchAnalisis();
  }, [image_id, navigate]);

  if (!data) {
    return <div>Cargando analisis...</div>;
  }
  const metrics = [
    {
      name: "Contraste",
      value: data.metrics[0],
      description: "Variación de luminancia",
      color: "fill-[#f52e70]",
    },
    {
      name: "Iluminación",
      value: data.metrics[1],
      description: "Claridad promedio",
      color: "fill-[#eca642]",
    },
    {
      name: "Balance",
      value: data.metrics[2],
      description: "Distribución del peso visual",
      color: "fill-[#3f8a76]",
    },
  ].map((metric) => ({
    ...metric,
    value: Number.isFinite(metric.value)
      ? Math.min(100, Math.max(0, metric.value))
      : 0,
  }));

  return (
    <PageFrame>
      <PageHeading
        eyebrow={"LECTURA VISUAL"}
        title="Resultado del análisis"
        description={
          <span className="inline-flex flex-wrap items-center gap-1">
            {data.artwork.title} · <DisplayDate value={data.artwork.date} /> ·{" "}
            <Badge
              tone={
                data.status === "Completado"
                  ? "green"
                  : data.status === "En progreso"
                    ? "pink"
                    : "amber"
              }
            >
              {data.status}
            </Badge>
          </span>
        }
        action={
          <PageLink to="/analize-image" secondary>
            + Analizar otra obra
          </PageLink>
        }
      />
      <div className="grid gap-[22px] xl:grid-cols-[.74fr_1fr]">
        <Panel>
          <div className="h-[300px] overflow-hidden rounded-xl sm:h-[385px]">
            <Artwork
              format="tall"
              kind="landscape"
              imageUrl={data.artwork.work_url}
              imageAlt={data.artwork.title}
            />
          </div>
          <h2 className="mt-5 text-[18px] font-bold [font-family:Georgia,serif]">
            Tu obra, tu autoría
          </h2>
          <p className="mt-3 text-[12px] leading-[19px] text-[#8b7b6b]">
            Visualizamos la imagen original sin modificarla. Las observaciones
            son una guía para tu aprendizaje, no una calificación estética.
          </p>
          <div className="mt-3">
            <PageLink to="/gallery" small secondary>
              Ver en mi galería →
            </PageLink>
          </div>
        </Panel>
        <div className="space-y-[18px]">
          <Panel>
            <SectionTitle>¿Qué observamos?</SectionTitle>
            <p className="mt-3 text-[12px] leading-5 text-[#8b7b6b]">
              Métricas descriptivas normalizadas de 0 a 100. Un número alto no
              significa necesariamente una obra “mejor”.
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              {metrics.map((metric) => (
                <div
                  key={metric.name}
                  className="rounded-xl border border-[#f0dfcf] bg-[#fdf8f1] p-4"
                >
                  <p className="text-[12px] text-[#8b7565]">{metric.name}</p>
                  <p className="mt-[7px] text-[26px] font-bold [font-family:Georgia,serif]">
                    {metric.value}/100
                  </p>
                  <svg
                    viewBox="0 0 100 5"
                    role="img"
                    aria-label={`${metric.name}: ${metric.value} de 100`}
                    className="mt-[10px] h-2 w-full"
                  >
                    <rect
                      width="100"
                      height="5"
                      rx="2.5"
                      className="fill-[#efeee7]"
                    />
                    <rect
                      width={metric.value}
                      height="5"
                      rx="2.5"
                      className={metric.color}
                    />
                  </svg>
                  <p className="mt-3 text-[10px] leading-4 text-[#8b7b6b]">
                    {metric.description}
                  </p>
                </div>
              ))}
            </div>
            <p className="mt-[18px] text-[12px] text-[#8b7565]">
              Paleta de {data.palette.length} colores dominantes (estimación
              visual)
            </p>
            <div
              className="mt-[10px] flex gap-2"
              aria-label="Paleta de la obra"
            >
              {data.palette.map(({ name, hex_color }, index) => (
                <svg
                  key={`${hex_color}-${index}`}
                  viewBox="0 0 28 28"
                  role="img"
                  aria-label={name}
                  className="size-[27px] rounded-full border-2 border-white ring-1 ring-[#dfd5c9]"
                >
                  <title>{name}</title>
                  <circle
                    cx="14"
                    cy="14"
                    r="14"
                    fill={
                      /^#[0-9a-f]{6}$/i.test(hex_color) ? hex_color : "#e5dfd5"
                    }
                  />
                </svg>
              ))}
            </div>
          </Panel>
          <Panel>
            <SectionTitle>La crítica educativa</SectionTitle>
            <p className="mt-3 text-[14px] leading-[24px] text-[#6d594a]">
              {data.critique}
            </p>
          </Panel>
          {data.exercise && (
            <Panel>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <SectionTitle>Ejercicio para seguir creciendo</SectionTitle>
                <Badge
                  tone={
                    data.exercise.status === "Completado"
                      ? "green"
                      : data.exercise.status === "En progreso"
                        ? "pink"
                        : "amber"
                  }
                >
                  {data.exercise.status}
                </Badge>
              </div>
              <p className="mt-5 text-[12px] leading-[19px] text-[#8b7b6b]">
                <strong className="text-[#654b36]">
                  {data.exercise.title}
                </strong>{" "}
                {data.exercise.description}
              </p>
              <div className="mt-3">
                <PageLink to="/exercise" small>
                  {data.exercise.status === "Completado"
                    ? "Ver ejercicios →"
                    : "Comenzar ejercicio →"}
                </PageLink>
              </div>
            </Panel>
          )}
        </div>
      </div>
    </PageFrame>
  );
}
