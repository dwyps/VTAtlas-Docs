import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const config: Config = {
  title: 'VT Atlas',
  tagline: 'Tag-driven regions and zones for Unreal Engine 5.8',
  // TODO: favicon once artwork exists. Same reason as the logo.

  future: {
    // OFF deliberately. v4 is unreleased and 3.10 was announced as the last v3.x minor, so this opts
    // into behaviour targeting a moving target for no benefit today. Turn it on when v4 ships and the
    // migration is being done on purpose. Reversing this is one line.
    v4: false,
  },

  url: 'https://docs.vestro.hr',
  baseUrl: '/',

  organizationName: 'dwyps',
  projectName: 'VTAtlas-Docs',

  // Both throw. The whole architecture rests on relative ./file.md links resolving, so a broken one
  // should be a build failure rather than a warning nobody reads.
  onBrokenLinks: 'throw',
  onBrokenAnchors: 'throw',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  markdown: {
    // THE LOAD-BEARING LINE. CommonMark rather than MDX is what lets docs/ be a real Obsidian vault:
    // no MDX parse failures on C++ generics, no JSX, no import statements, no per-file switching. The
    // documented cost (issue 9092) is losing <Tabs>, live code blocks and per-page <head> injection.
    // None of those are used here; title, description and og tags come from frontmatter and this file.
    format: 'md',
    mermaid: true,
    hooks: {
      // Verified against @docusaurus/types 3.10.2: the top-level onBrokenMarkdownLinks still exists
      // but carries a "TODO Docusaurus v4 remove" comment, and markdown.hooks is the forward-compatible
      // home. Set here so it survives the v4 migration.
      onBrokenMarkdownLinks: 'throw',
      onBrokenMarkdownImages: 'throw',
    },
  },

  themes: [
    '@docusaurus/theme-mermaid',
    [
      // Local search rather than Algolia. Algolia's DocSearch terms require displaying their logo
      // linking back to algolia.com on the search UI, and eligibility is by application. Neither
      // belongs on a paid product's own documentation.
      require.resolve('@easyops-cn/docusaurus-search-local'),
      {hashed: true, indexBlog: false, docsRouteBasePath: '/docs'},
    ],
  ],

  presets: [
    [
      'classic',
      {
        docs: {
          path: 'docs',
          routeBasePath: 'docs',
          sidebarPath: './sidebars.ts',
          breadcrumbs: true,
          // Versioning is NOT switched on: one docs/ folder, one copy in the vault. But the URL shape
          // is set today, because that is the part which is expensive to change later. This yields
          // /docs/1.0/... from a single source tree, with a real version label in the navbar.
          //
          // The trigger to actually cut a version is not shipping 1.1. It is the first time an engine
          // version is DROPPED from the supported set while development continues, because studios
          // frozen on that engine still need their docs reachable.
          lastVersion: 'current',
          versions: {
            current: {label: '1.0', path: '1.0'},
          },
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    // TODO: og card at 1200x630 once artwork exists. Omitted rather than shipping
    // Docusaurus's own social card.
    colorMode: {
      defaultMode: 'dark',
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'VT Atlas',
      // TODO: logo once artwork exists. Title-only for now rather than Docusaurus's logo.
      items: [
        {type: 'docSidebar', sidebarId: 'docsSidebar', position: 'left', label: 'Documentation'},
        {type: 'docsVersionDropdown', position: 'right'},
        {href: 'https://vestro.hr/#contact', label: 'Support', position: 'right'},
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Documentation',
          items: [
            {label: 'Setup', to: '/docs/1.0/getting-started/setup'},
            {label: 'Concepts', to: '/docs/1.0/concepts'},
            {label: 'API Tour', to: '/docs/1.0/reference/api-tour'},
          ],
        },
        {
          title: 'Support',
          items: [
            {label: 'Troubleshooting', to: '/docs/1.0/support/troubleshooting'},
            {label: 'Contact', href: 'https://vestro.hr/#contact'},
          ],
        },
        {
          title: 'Vestro',
          items: [{label: 'vestro.hr', href: 'https://vestro.hr/'}],
        },
      ],
      copyright: `Copyright (c) ${new Date().getFullYear()} Vestro, Fran Grgec.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['cpp', 'ini'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
