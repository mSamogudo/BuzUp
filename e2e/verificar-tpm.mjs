import { chromium } from '@playwright/test'
import { mkdir } from 'node:fs/promises'

const BASE = 'http://localhost:3099'
const D = '/tmp/capturas-tpm'
await mkdir(D, { recursive: true })
const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, locale: 'pt-PT' })
const page = await ctx.newPage()
page.on('console', (m) => { if (m.type() === 'error') console.log('CONSOLE ERRO:', m.text().split('\n')[0]) })
page.on('pageerror', (e) => console.log('PAGE ERRO:', e.message.split('\n')[0]))

async function shot(nome, url, tema) {
  await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 60_000 })
  await page.waitForFunction(() => !document.querySelector('.splash-screen'), null, { timeout: 30_000 })
  await page.evaluate((t) => localStorage.setItem('busup_landing_theme', t), tema)
  await page.reload({ waitUntil: 'networkidle' })
  await page.waitForFunction(() => !document.querySelector('.splash-screen'), null, { timeout: 30_000 })
  await page.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)) }
    window.scrollTo(0, 0)
    for (const img of document.images) img.loading = 'eager'
  })
  await page.waitForTimeout(900)
  await page.screenshot({ path: `${D}/${nome}-${tema}.png`, fullPage: true })
  console.log('ok', nome, tema)
}

await shot('tpm-landing', '/tpm-tur', 'light')
await shot('tpm-landing', '/tpm-tur', 'dark')
await shot('busup-landing', '/', 'light')
await shot('login', '/login', 'light')
await shot('comprar', '/comprar', 'light')
await b.close()
