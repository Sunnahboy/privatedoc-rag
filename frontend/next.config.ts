import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  //Allow local network IP to access the dev server
  allowedDevOrigins: ["192.168.150.135"],
};

export default nextConfig;
