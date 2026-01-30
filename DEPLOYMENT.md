# Causal Finance - Deployment Ready

A sophisticated portfolio management and causal analysis platform combining real-time market data, machine learning predictions, and causal inference for smarter investment decisions.

## 🚀 Quick Deploy

### Backend (Render)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

1. Fork this repository
2. Connect to Render
3. Use `render.yaml` for automatic configuration
4. Set environment variables (see below)

### Frontend (Vercel)
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/import/project)

1. Import repository to Vercel
2. Set root directory to `frontend`
3. Add `VITE_API_URL` environment variable

## 📋 Environment Variables

### Backend (Required)
| Variable | Description | Example |
|----------|-------------|---------|
| `FLASK_ENV` | Environment mode | `production` |
| `SECRET_KEY` | Flask secret key | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_SECRET_KEY` | JWT signing key | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | PostgreSQL URL | Auto-provided by Render |
| `CORS_ORIGINS` | Frontend URLs | `https://your-app.vercel.app` |
| `FRED_API_KEY` | FRED API key | Get free: https://fred.stlouisfed.org |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage key | Get free: https://alphavantage.co |

### Frontend (Required)
| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `https://your-api.onrender.com/api` |

## 🛠️ Local Development

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your values
python run.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 📁 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── models/      # Database models
│   │   ├── routes/      # API endpoints
│   │   └── services/    # Business logic
│   ├── config.py        # Configuration
│   ├── wsgi.py          # Production entry point
│   ├── Procfile         # Render/Heroku config
│   └── render.yaml      # Render blueprint
│
├── frontend/
│   ├── src/
│   │   ├── pages/       # React pages
│   │   ├── components/  # UI components
│   │   ├── lib/         # API & hooks
│   │   └── contexts/    # React contexts
│   ├── vercel.json      # Vercel config
│   └── public/_redirects # SPA routing
```

## 🔑 Features

- **Portfolio Builder** - Create and optimize portfolios with AI
- **Scenario Simulator** - Test portfolios against economic shocks
- **Causal Analysis** - Understand cause-effect relationships
- **Paper Trading** - Practice trading with virtual money
- **ML Predictions** - Market regime detection & sector forecasts
- **Real-time Data** - Live stock prices and market indicators

## 📄 License

MIT License - See [LICENSE](LICENSE) file

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request
