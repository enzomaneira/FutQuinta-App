// Guarda o JWT no localStorage (app interno, só organizadores)
const TOKEN_KEY = 'futquinta.token'

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token) {
  try {
    localStorage.setItem(TOKEN_KEY, token)
  } catch {
    // modo privado ou armazenamento bloqueado: segue só nesta aba
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY)
  } catch {
    // ignora
  }
}
