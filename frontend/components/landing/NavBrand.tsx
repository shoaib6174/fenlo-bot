import Link from 'next/link';

/**
 * Nav brand for architecture, use-cases pages.
 * Server component.
 */
export async function TechNavBrand() {
  return (
    <Link href="/" className="flex items-center gap-2">
      <span className="text-2xl font-serif tracking-tight text-[var(--color-text-primary)]">
        Fenlo AI
      </span>
    </Link>
  );
}

/**
 * Footer brand for architecture, use-cases pages.
 */
export async function TechFooterBrand() {
  return (
    <span className="text-xl font-serif text-[var(--color-text-primary)]">Fenlo AI</span>
  );
}

/**
 * Light nav brand (used on integrations, status, docs pages).
 * Server component.
 */
export async function LightNavBrand() {
  return (
    <Link href="/" className="flex items-center gap-2">
      <span className="text-xl font-serif text-[var(--color-text-primary)]">Fenlo AI</span>
    </Link>
  );
}

/**
 * Light footer copyright.
 */
export async function LightFooterBrand() {
  return <>&copy; 2026 Fenlo AI. All rights reserved.</>;
}

/**
 * Docs-style nav brand with icon (used on zapier-integration page).
 */
export async function DocsNavBrand() {
  return (
    <Link href="/" className="flex items-center gap-2">
      <span className="text-xl font-serif text-gray-900 dark:text-white">Fenlo AI</span>
    </Link>
  );
}

/**
 * Docs-style footer brand with icon (used on zapier-integration page).
 */
export async function DocsFooterBrand() {
  return (
    <span className="font-serif text-gray-900 dark:text-white">Fenlo AI</span>
  );
}

/**
 * Dark terminal-style brand (used on api-quickstart page).
 */
export async function DarkNavBrand() {
  return (
    <Link href="/" className="text-gray-400 hover:text-white text-sm flex items-center gap-1">
      <span className="rotate-180 inline-block">&rarr;</span>
      Back to Fenlo AI
    </Link>
  );
}
