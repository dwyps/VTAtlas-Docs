import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={siteConfig.title}
      description="Tag-driven regions and zones for Unreal Engine 5.8. Place a volume, give it a gameplay tag, and ask where an actor is.">
      <header className={styles.hero}>
        <div className="container">
          <Heading as="h1" className={styles.heroTitle}>
            VT&nbsp;Atlas
          </Heading>
          <p className={styles.heroTagline}>{siteConfig.tagline}</p>
          <p className={styles.heroBody}>
            Place a volume, give it a gameplay tag, and get three honest answers: is this actor in that
            region, which single region is it in, and who is inside it. Boxes, spheres, capsules and
            splines. Everything callable from Blueprint.
          </p>
          <div className={styles.heroButtons}>
            <Link className="button button--primary button--lg" to="/docs/1.0/getting-started/setup">
              Get started
            </Link>
            <Link className="button button--secondary button--lg" to="/docs/1.0/overview">
              Read the overview
            </Link>
          </div>
          <p className={styles.heroMeta}>Unreal Engine 5.8 &middot; Windows and Mac &middot; no plugin dependencies</p>
        </div>
      </header>
    </Layout>
  );
}
