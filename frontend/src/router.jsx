import { createBrowserRouter } from 'react-router'

import AppLayout from './components/AppLayout.jsx'
import RequireAuth from './components/RequireAuth.jsx'
import CalendarPage from './pages/CalendarPage.jsx'
import DropInsPage from './pages/DropInsPage.jsx'
import FinancePage from './pages/FinancePage.jsx'
import GamePage from './pages/GamePage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import HomePage from './pages/HomePage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'
import PlayerPage from './pages/PlayerPage.jsx'
import PlayersPage from './pages/PlayersPage.jsx'
import SettingsPage from './pages/SettingsPage.jsx'

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: (
      <RequireAuth>
        <AppLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <HomePage /> },
      { path: 'calendario', element: <CalendarPage /> },
      { path: 'jogo', element: <GamePage /> },
      { path: 'jogos/:id', element: <GamePage /> },
      { path: 'jogadores', element: <PlayersPage /> },
      { path: 'jogadores/:id', element: <PlayerPage /> },
      { path: 'financeiro', element: <FinancePage /> },
      { path: 'avulsos', element: <DropInsPage /> },
      { path: 'historico', element: <HistoryPage /> },
      { path: 'historico/:id', element: <HistoryPage /> },
      { path: 'configuracoes', element: <SettingsPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
