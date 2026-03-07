import { headers } from 'next/headers';
import { getSkinFromHost } from '@/lib/skin';
import FenloaiLanding from '@/components/landing/FenloaiLanding';
import RagchatLanding from '@/components/landing/RagchatLanding';

export default async function Home() {
  const headersList = await headers();
  const host = headersList.get('host') || '';
  const skin = getSkinFromHost(host);

  if (skin === 'ragchat') return <RagchatLanding />;
  return <FenloaiLanding />;
}
