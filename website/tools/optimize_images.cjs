#!/usr/bin/env node
'use strict';

/**
 * Create delivery copies only; the published-source images remain untouched.
 * Requires Node.js 18+ and sharp installed locally or in --modules NODE_MODULES.
 *
 *   node tools/optimize_images.cjs --modules /path/to/node_modules
 *   node tools/optimize_images.cjs --modules /path/to/node_modules --check
 *
 * --check is read-only: it re-creates the expected images in memory, checks the
 * source-to-delivery manifest and fully decodes every delivery WebP. The site
 * root is determined from this script's location, not the current directory.
 */

const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');

const ROOT = path.resolve(__dirname, '..');
const MANIFEST = path.join(ROOT, '_data', 'delivery_images.json');
const DELIVERY_DIR = path.join(ROOT, 'images', 'site');
const RECIPE_VERSION = 1;
const DELIVERY_PATH = /^\/images\/site\/[a-z0-9_-]+-[a-f0-9]{10}\.webp$/;

function argumentsFrom(argv) {
  const result = {check: false, modules: null, help: false};
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--check') result.check = true;
    else if (argv[i] === '--help' || argv[i] === '-h') result.help = true;
    else if (argv[i] === '--modules' && argv[i + 1] && !argv[i + 1].startsWith('--')) {
      result.modules = path.resolve(argv[++i]);
    } else throw new Error(`Unknown or incomplete option: ${argv[i]}`);
  }
  return result;
}

async function readJson(file, optional = false) {
  try {
    return JSON.parse((await fs.readFile(file, 'utf8')).replace(/^\uFEFF/, ''));
  } catch (error) {
    if (optional && error.code === 'ENOENT') return null;
    throw error;
  }
}

function imageFile(src) {
  if (typeof src !== 'string' || !src.startsWith('/images/') || /[\\?#]/.test(src)) {
    throw new Error(`Expected a local /images/ source URL: ${src}`);
  }
  const resolved = path.resolve(ROOT, src.slice(1));
  const relative = path.relative(path.join(ROOT, 'images'), resolved);
  if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error(`Image source escapes the images directory: ${src}`);
  }
  if (src.startsWith('/images/site/')) throw new Error(`Delivery image used as an original source: ${src}`);
  return resolved;
}

async function sourceList() {
  const sources = new Map();
  function add(src, maxEdge, quality) {
    imageFile(src);
    const old = sources.get(src);
    sources.set(src, {
      src,
      maxEdge: Math.max(old?.maxEdge || 0, maxEdge),
      quality: Math.max(old?.quality || 0, quality)
    });
  }
  function visit(value, maxEdge, quality) {
    if (!value || typeof value !== 'object') return;
    if (typeof value.image === 'string') {
      add(value.image, maxEdge, value.image_fit === 'contain' ? 90 : quality);
    }
    Object.values(value).forEach(child => visit(child, maxEdge, quality));
  }
  for (const [file, maxEdge, quality] of [
    ['lab.json', 1000, 95],
    ['team.json', 640, 82],
    ['news.json', 800, 82],
    ['research.json', 1280, 90],
    ['home.json', 1800, 86],
    ['milestones.json', 1800, 88],
    ['platform.json', 1600, 90]
  ]) visit(await readJson(path.join(ROOT, '_data', file)), maxEdge, quality);

  // Shared photographs and legacy research figures remain useful to templates.
  for (const [name, maxEdge, quality] of [
    ['group2.png', 1600, 82],
    ['field_trip_hongkai.png', 1600, 82],
    ['site_sandy_beach.png', 1600, 82],
    ['research_topic1.png', 1280, 90],
    ['research_topic2.png', 1280, 90],
    ['prb_ch4.png', 1280, 90],
    ['prb_micro.png', 1280, 90]
  ]) {
    const src = `/images/${name}`;
    try {
      await fs.access(imageFile(src));
      add(src, maxEdge, quality);
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
  }
  return [...sources.values()].sort((a, b) => a.src < b.src ? -1 : a.src > b.src ? 1 : 0);
}

async function writeIfChanged(file, bytes) {
  try {
    if ((await fs.readFile(file)).equals(bytes)) return false;
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  await fs.writeFile(file, bytes);
  return true;
}

async function optimize(source, sharp, check) {
  // SVGs retain their scalable original. Animated originals retain all frames.
  if (/\.svg$/i.test(source.src)) return {skipped: source.src};
  const input = await fs.readFile(imageFile(source.src));
  const metadata = await sharp(input, {animated: true}).metadata();
  if (metadata.format === 'svg' || (metadata.pages || 1) > 1) return {skipped: source.src};

  const recipe = {version: RECIPE_VERSION, maxEdge: source.maxEdge, quality: source.quality};
  const hash = crypto.createHash('sha256').update(source.src).update('\0').update(input)
    .update(JSON.stringify(recipe)).digest('hex').slice(0, 10);
  const stem = path.posix.basename(source.src, path.posix.extname(source.src)).toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'image';
  const src = `/images/site/${stem}-${hash}.webp`;
  const outputFile = path.join(ROOT, src.slice(1));

  let output;
  // Avoid another lossy recompression when an existing WebP fits its bounds.
  const fits = metadata.width <= source.maxEdge && metadata.height <= source.maxEdge;
  if (metadata.format === 'webp' && fits && (!metadata.orientation || metadata.orientation === 1)) {
    output = input;
  } else {
    output = await sharp(input).rotate().resize({
      width: source.maxEdge, height: source.maxEdge, fit: 'inside', withoutEnlargement: true
    }).webp({quality: source.quality, effort: 4}).toBuffer();
  }
  const expected = await sharp(output).metadata();
  const entry = {src, width: expected.width, height: expected.height, source_bytes: input.length, bytes: output.length};
  let changed = false;
  if (check) {
    const saved = await fs.readFile(outputFile);
    if (!saved.equals(output)) throw new Error(`Delivery image is stale or changed: ${src}`);
  } else changed = await writeIfChanged(outputFile, output);

  const actual = await sharp(outputFile).metadata();
  if (actual.format !== 'webp' || actual.width !== entry.width || actual.height !== entry.height) {
    throw new Error(`Invalid delivery image dimensions or format: ${src}`);
  }
  await sharp(outputFile).stats(); // Force complete pixel decoding, not just header parsing.
  return {source: source.src, entry, changed};
}

async function main() {
  const args = argumentsFrom(process.argv.slice(2));
  if (args.help) {
    console.log('Usage: node tools/optimize_images.cjs [--modules NODE_MODULES] [--check]');
    return;
  }
  let sharp;
  try {
    sharp = args.modules ? require(path.join(args.modules, 'sharp')) : require('sharp');
  } catch (error) {
    throw new Error('sharp is required. Install it locally or provide --modules /path/to/node_modules.', {cause: error});
  }
  sharp.concurrency(1);
  const sources = await sourceList();
  const previous = await readJson(MANIFEST, true);
  if (!args.check) await fs.mkdir(DELIVERY_DIR, {recursive: true});

  // Two images at a time bounds memory use. The indexed results retain source order.
  const results = new Array(sources.length);
  let next = 0;
  async function worker() {
    while (next < sources.length) {
      const index = next++;
      results[index] = await optimize(sources[index], sharp, args.check);
    }
  }
  await Promise.all([worker(), worker()]);
  const manifest = Object.fromEntries(results.filter(item => !item.skipped).map(item => [item.source, item.entry]));
  const manifestBytes = Buffer.from(`${JSON.stringify(manifest, null, 2)}\n`);
  if (args.check) {
    if (!previous || !(await fs.readFile(MANIFEST)).equals(manifestBytes)) {
      throw new Error('Delivery manifest is missing or stale. Run the optimizer without --check.');
    }
  } else {
    await writeIfChanged(MANIFEST, manifestBytes);
    // Remove only obsolete generated files explicitly recorded in our old manifest.
    const retained = new Set(Object.values(manifest).map(item => item.src));
    for (const old of Object.values(previous || {})) {
      if (old && DELIVERY_PATH.test(old.src) && !retained.has(old.src)) {
        await fs.rm(path.join(ROOT, old.src.slice(1)), {force: true});
      }
    }
  }

  const entries = Object.values(manifest);
  const sourceBytes = entries.reduce((sum, item) => sum + item.source_bytes, 0);
  const deliveryBytes = entries.reduce((sum, item) => sum + item.bytes, 0);
  const saved = sourceBytes ? (100 * (sourceBytes - deliveryBytes) / sourceBytes).toFixed(1) : '0.0';
  const changed = results.filter(item => item.changed).length;
  console.log(`${args.check ? 'Verified' : 'Generated'} ${entries.length} delivery images; ${sourceBytes} -> ${deliveryBytes} bytes (${saved}% smaller).`);
  if (!args.check) console.log(`${changed} image files changed; unchanged files retain their modification times.`);
  const skipped = results.filter(item => item.skipped).map(item => item.skipped);
  if (skipped.length) console.log(`Scalable or animated originals retained: ${skipped.join(', ')}`);
}

main().catch(error => {
  console.error(`Image delivery check failed: ${error.message}`);
  process.exitCode = 1;
});
