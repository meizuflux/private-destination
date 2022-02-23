import { lazy } from 'solid-js';
import type { RouteDefinition } from 'solid-app-router';

import Home from './pages/home';
import AboutData from './pages/about.data';

import { wrappedRedirect } from './utils/redirect';

export const routes: RouteDefinition[] = [
  {
    path: '/',
    component: Home,
  },
  {
    path: '/about',
    component: lazy(() => import('./pages/about')),
    data: AboutData,
  },
  {
    path: "/callback",
    component: lazy(() => import("./pages/callback")),
  },
  {
    path: "/p",
    component: lazy(() => import("./pages/protected")),
  },
  {
    path: "/login",
    component: lazy(() => wrappedRedirect("https://discord.com/api/oauth2/authorize?client_id=943699345818153000&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fcallback&response_type=token&scope=identify%20email"))
  },
  {
    path: '**',
    component: lazy(() => import('./errors/404')),
  },
];
