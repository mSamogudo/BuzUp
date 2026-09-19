import { test as setup, expect } from '@playwright/test'
import { FICHEIRO_SESSAO } from '../playwright.config'

/** Credenciais do ambiente de desenvolvimento (`make ensure-superadmin`).
 *  Nao ha segredos aqui: so existem no contentor descartavel. */
const UTILIZADOR = process.env.BUZUP_USER ?? 'admin'
const SENHA = process.env.BUZUP_PASS ?? 'admin'

setup('autentica e guarda a sessao', async ({ page }) => {
  await page.goto('/login')

  // O formulario so responde depois de hidratar; esperar pelo campo
  // e mais fiavel do que esperar por tempo.
  const utilizador = page.getByRole('textbox').first()
  await expect(utilizador).toBeVisible()
  await utilizador.fill(UTILIZADOR)
  await page.locator('input[type=password]').fill(SENHA)
  await page.getByRole('button', { name: /entrar/i }).first().click()

  await page.waitForURL(/\/app/, { timeout: 30_000 })
  await expect(page.getByRole('navigation').first()).toBeVisible()

  await page.context().storageState({ path: FICHEIRO_SESSAO })
})
