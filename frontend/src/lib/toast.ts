import { toast } from "sonner";

export function showToast(tone: "success" | "danger" | "neutral", message: string) {
  if (tone === "success") toast.success(message);
  else if (tone === "danger") toast.error(message);
  else toast(message);
}
