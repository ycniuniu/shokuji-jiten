export type PhotoCredit = {
  title: string
  author: string
  license: string
  license_url: string | null
  page_url: string
}

let cache: Promise<Record<string, PhotoCredit>> | null = null

function loadCredits(): Promise<Record<string, PhotoCredit>> {
  if (!cache) {
    cache = fetch('/images/credits.json')
      .then((r) => (r.ok ? r.json() : {}))
      .catch(() => ({}))
  }
  return cache
}

/** Credit for an image path such as "/images/apple_pie.jpg", if any. */
export async function creditFor(imagePath: string): Promise<PhotoCredit | null> {
  const key = imagePath.replace(/^.*\//, '').replace(/\.[a-z]+$/i, '')
  const all = await loadCredits()
  return all[key] ?? null
}
