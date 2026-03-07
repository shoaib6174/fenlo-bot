#!/usr/bin/env node
/**
 * esbuild bundler for BotForge widget
 *
 * Builds standalone embeddable widget with:
 * - Preact (3KB runtime)
 * - IIFE format (no module loader needed)
 * - Content hash for cache-busting
 * - Size budget enforcement (< 50KB)
 * - Minification + tree-shaking
 */

import * as esbuild from 'esbuild';
import { createHash } from 'crypto';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const isWatch = process.argv.includes('--watch');
const distDir = join(__dirname, 'dist');

// Ensure dist directory exists
if (!existsSync(distDir)) {
  mkdirSync(distDir, { recursive: true });
}

/**
 * Generate content hash for cache-busting
 */
function generateHash(content) {
  return createHash('sha256').update(content).digest('hex').slice(0, 8);
}

/**
 * Check bundle size against budget
 */
function checkSizeBudget(filepath, maxSizeKB = 50) {
  const stats = readFileSync(filepath);
  const sizeKB = (stats.length / 1024).toFixed(2);

  console.log(`\n📦 Bundle size: ${sizeKB} KB`);

  if (stats.length > maxSizeKB * 1024) {
    console.error(`\n❌ Bundle exceeds ${maxSizeKB}KB budget!`);
    process.exit(1);
  } else {
    console.log(`✅ Within ${maxSizeKB}KB budget\n`);
  }

  return sizeKB;
}

/**
 * Build configuration
 */
const buildConfig = {
  entryPoints: [join(__dirname, 'src/index.tsx')],
  bundle: true,
  minify: true,
  format: 'iife',
  target: ['es2020'],
  outfile: join(distDir, 'widget.js'), // Temporary, will be renamed with hash
  define: {
    'process.env.NODE_ENV': '"production"',
    'WIDGET_VERSION': '"1.0.0"',
    'SUPPORTED_API_VERSION': '1', // API version the widget supports
  },
  jsxFactory: 'h',
  jsxFragment: 'Fragment',
  jsx: 'transform',
  alias: {
    'react': 'preact/compat',
    'react-dom': 'preact/compat',
  },
  loader: {
    '.css': 'text', // Import CSS as string for shadow DOM
  },
  logLevel: 'info',
};

/**
 * Build the widget
 */
async function build() {
  try {
    console.log('🏗️  Building BotForge widget...\n');

    // Build with esbuild
    const result = await esbuild.build(buildConfig);

    // Read the output
    const tempOutput = join(distDir, 'widget.js');
    const bundleContent = readFileSync(tempOutput, 'utf-8');

    // Generate content hash
    const hash = generateHash(bundleContent);
    const finalFilename = `widget.${hash}.js`;
    const finalPath = join(distDir, finalFilename);

    // Rename with hash
    writeFileSync(finalPath, bundleContent);

    // Check size budget
    const sizeKB = checkSizeBudget(finalPath, 50);

    // Write metadata for CI/deployment
    const metadata = {
      filename: finalFilename,
      hash,
      size: `${sizeKB} KB`,
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    };
    writeFileSync(
      join(distDir, 'widget-metadata.json'),
      JSON.stringify(metadata, null, 2)
    );

    console.log(`✅ Widget built successfully: ${finalFilename}`);

    // Clean up temp file
    if (existsSync(tempOutput) && tempOutput !== finalPath) {
      const { unlinkSync } = await import('fs');
      unlinkSync(tempOutput);
    }
  } catch (error) {
    console.error('❌ Build failed:', error);
    process.exit(1);
  }
}

/**
 * Watch mode
 */
async function watch() {
  console.log('👀 Watching for changes...\n');

  const ctx = await esbuild.context({
    ...buildConfig,
    plugins: [
      {
        name: 'rebuild-notify',
        setup(build) {
          build.onEnd((result) => {
            if (result.errors.length === 0) {
              console.log('✅ Rebuild complete');
              // Note: Size check and hash generation only happen in production build
            }
          });
        },
      },
    ],
  });

  await ctx.watch();
}

// Run build or watch
if (isWatch) {
  watch();
} else {
  build();
}
