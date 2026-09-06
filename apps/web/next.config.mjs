/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',

  typescript: {
    // @vitejs/plugin-react has broken type definitions that conflict with Next.js build.
    // Our source code is type-checked separately via `tsc --noEmit`.
    ignoreBuildErrors: true,
  },

  // Keep firebase-admin as external for server-side only
  experimental: {
    serverComponentsExternalPackages: ['firebase-admin'],
  },

  // Ensure firebase-admin and its Node.js dependencies are not bundled for the client
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
        child_process: false,
      };
    }
    return config;
  },

  // ISR is supported by default with App Router - use `revalidate` in page/layout exports
  // or `revalidatePath`/`revalidateTag` for on-demand revalidation

  async redirects() {
    return [];
  },

  async rewrites() {
    return [
      // Static wedding site under public/casamento/ — served as a plain HTML/CSS/JS
      // bundle, not a Next.js route. /casamento has no dot in the path, so it isn't
      // resolved to public/casamento/index.html automatically.
      {
        source: '/casamento',
        destination: '/casamento/index.html',
      },
    ];
  },

  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
        ],
      },
    ];
  },
};

export default nextConfig;
