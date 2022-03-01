import type { Component } from 'solid-js';
import { Link, useRoutes, useLocation } from 'solid-app-router';

import { routes } from './routes';

const App: Component = () => {
  const Route = useRoutes(routes);

  return (
    <>
        <nav class="navbar" role="navigation" aria-label="main navigation">
            <div class="navbar-brand">
                <a class="navbar-item" href="https://bulma.io">
                <img src="https://bulma.io/images/bulma-logo.png" width="112" height="28" />
                </a>

                <a role="button" class="navbar-burger" aria-label="menu" aria-expanded="false" data-target="navbarBasicExample">
                <span aria-hidden="true"></span>
                <span aria-hidden="true"></span>
                <span aria-hidden="true"></span>
                </a>
            </div>

            <div id="navbarBasicExample" class="navbar-menu">
                <div class="navbar-start">
                <a class="navbar-item" href="/about">
                    About
                </a>

                <a class="navbar-item" href="/dashboard">
                    Dashboard
                </a>

                </div>

                <div class="navbar-end">
                <div class="navbar-item">
                    <div class="buttons">
                    <a class="button is-primary" href="/login?signup=true">
                        <strong>Sign up</strong>
                    </a>
                    <a class="button is-light" href="/login">
                        Log in
                    </a>
                    </div>
                </div>
                </div>
            </div>
        </nav>
        <Route />
    </>
  );
};

export default App;
