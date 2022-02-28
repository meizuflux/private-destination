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
    component: lazy(() => import("./pages/login"))
  },
  {
    path: "/user",
    component: lazy(() => import("./pages/user"))
  },
  {
    path: '**',
    component: lazy(() => import('./errors/404')),
  },
];
