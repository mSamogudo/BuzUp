import { useCallback, useEffect, useRef } from "react";
import { MapPin, RefreshCw } from "lucide-react";
import { apiFetch } from "../lib/api";
import { t } from "../lib/i18n";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { PageFrame, useAsyncData } from "../ui/common";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

interface DeviceLocation {
  id: number;
  serial_number: string;
  device_type: string;
  manufacturer: string;
  model_name: string;
  status: string;
  last_latitude: number | null;
  last_longitude: number | null;
  last_speed: number | null;
  last_location_at: string | null;
  app_version: string;
}

export default function MapPage() {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<L.Map | null>(null);

  const loader = useCallback(() =>
    apiFetch("/api/admin/devices/", token!).then((d) => {
      const rows = d.results || d;
      return rows.filter((dev: DeviceLocation) => dev.last_latitude && dev.last_longitude);
    }),
  [token]);
  const { data: devices, loading, reload } = useAsyncData<DeviceLocation[]>(loader, [token]);

  useEffect(() => {
    if (!mapRef.current || mapInstance.current) return;

    mapInstance.current = L.map(mapRef.current).setView([-25.9692, 32.5732], 12);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; OpenStreetMap',
      maxZoom: 18,
    }).addTo(mapInstance.current);

    return () => {
      mapInstance.current?.remove();
      mapInstance.current = null;
    };
  }, []);

  useEffect(() => {
    if (!mapInstance.current || !devices) return;

    mapInstance.current.eachLayer((layer) => {
      if (layer instanceof L.Marker) mapInstance.current!.removeLayer(layer);
    });

    const busIcon = L.divIcon({
      html: `<div style="background:#1D5FA7;color:#fff;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;box-shadow:0 2px 8px rgba(0,0,0,0.3);border:2px solid #fff;">🚌</div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 16],
      className: "",
    });

    devices.forEach((dev) => {
      if (!dev.last_latitude || !dev.last_longitude) return;

      const marker = L.marker([dev.last_latitude, dev.last_longitude], { icon: busIcon });
      marker.bindPopup(`
        <div style="font-family:Inter,sans-serif;min-width:180px;">
          <strong style="font-size:14px;">${dev.serial_number}</strong><br/>
          <span style="font-size:12px;color:#71717a;">${dev.manufacturer} ${dev.model_name}</span><br/>
          <span style="font-size:11px;color:#71717a;">Velocidade: ${dev.last_speed ? dev.last_speed + " km/h" : "-"}</span><br/>
          <span style="font-size:11px;color:#71717a;">Ultima posicao: ${dev.last_location_at ? new Date(dev.last_location_at).toLocaleString("pt-MZ") : "-"}</span>
        </div>
      `);
      marker.addTo(mapInstance.current!);
    });

    if (devices.length > 0) {
      const bounds = L.latLngBounds(devices.map((d) => [d.last_latitude!, d.last_longitude!] as [number, number]));
      mapInstance.current.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [devices]);

  return (
    <PageFrame kicker={t(lc, "operation")} title="Mapa"
      action={<button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={15} /><span>{t(lc, "refresh")}</span></button>}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12, fontSize: 13, color: "var(--app-text-muted)" }}>
        <MapPin size={14} />
        <span>{loading ? "A carregar..." : `${(devices || []).length} terminais com localizacao`}</span>
      </div>
      <div ref={mapRef} style={{ width: "100%", height: "calc(100vh - 240px)", minHeight: 400, borderRadius: 12, border: "1px solid var(--app-border)", overflow: "hidden" }} />
    </PageFrame>
  );
}
