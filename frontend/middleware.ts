import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that REQUIRE authentication (write/edit operations)
const authRequiredRoutes = [
  '/settings',
  '/admin',
  '/inbox',
  '/voice',
  '/channels',
];

function isRagchatSkin(request: NextRequest): boolean {
  const host = request.headers.get('host') || '';
  const hostname = host.split(':')[0].toLowerCase();
  const forced = process.env.NEXT_PUBLIC_FORCE_SKIN;
  if (forced === 'ragchat') return true;
  return hostname === 'rag.fenloai.com' || hostname.startsWith('ragchat.');
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const ragchat = isRagchatSkin(request);

  // Public share pages (/p/[token]/*) — always accessible
  if (pathname.startsWith('/p/')) {
    return NextResponse.next();
  }

  // RAGChat standalone mode — redirect root to /why-ragchat (sales landing)
  if (ragchat && pathname === '/') {
    return NextResponse.redirect(new URL('/why-ragchat', request.url));
  }

  // RAGChat standalone mode — no login/register, redirect to landing
  if (ragchat && (pathname === '/login' || pathname === '/register')) {
    return NextResponse.redirect(new URL('/why-ragchat', request.url));
  }

  // Check if route requires auth
  const needsAuth = authRequiredRoutes.some(route =>
    pathname.startsWith(route)
  );

  const hasAuthCookie = request.cookies.has('access_token');

  // Redirect to login only for write-operation routes
  if (needsAuth && !hasAuthCookie) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Redirect to dashboard if accessing login/register while authenticated
  if ((pathname === '/login' || pathname === '/register') && hasAuthCookie) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|widget).*)',
  ],
};
