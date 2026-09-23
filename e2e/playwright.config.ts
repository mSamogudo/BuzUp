import { defineConfig, devices } from '@playwright/test'

/** O ambiente de desenvolvimento do proprio projecto (`make dev-up-d`).
 *  Sobrepoe-se com BUZUP_BASE_URL quando se aponta para staging. */
const baseURL = process.env.BUZUP_BASE_URL ?? 'http://localhost:3008'

/** Sessao guardada uma vez pelo projecto `setup` e reutilizada pelos restantes. */
export const FICHEIRO_SESSAO = 'playwright/.auth/admin.json'

export default defineConfig({
  testDir: './tests',
  // Estes testes partilham uma sessao autenticada e tocam nos mesmos dados.
  // Em serie, uma falha aponta para uma regressao e nao para uma corrida.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  timeout: 45_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL,
    // O portal e uma SPA pesada: sem folga, um clique cedo demais falha
    // por hidratacao incompleta e nao por regressao.
    actionTimeout: 15_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    viewport: { width: 1440, height: 900 },
    locale: 'pt-PT',
    timezoneId: 'Africa/Maputo',
  },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      // Paginas que nao pedem sessao. Correm sem depender do `setup`, por
      // isso uma falha de autenticacao nao as arrasta consigo.
      name: 'publicas',
      testMatch: [/publicas\.spec\.ts/, /hero-busca\.spec\.ts/],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'portal',
      testIgnore: [/publicas\.spec\.ts/, /hero-busca\.spec\.ts/, /.*\.setup\.ts/],
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'], storageState: FICHEIRO_SESSAO },
    },
  ],
})
