import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "TradeBrain · Quantitative Trading Desk",
    short_name: "TradeBrain",
    description: "Acompanhamento seguro das operações na Binance Spot Testnet.",
    start_url: "/",
    display: "standalone",
    orientation: "any",
    background_color: "#080b0f",
    theme_color: "#080b0f",
    categories: ["finance", "productivity"],
    lang: "pt-BR",
  };
}
