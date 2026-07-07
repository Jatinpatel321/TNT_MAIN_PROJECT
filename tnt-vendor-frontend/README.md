# TNT Vendor App

React Native mobile application for campus vendors to manage orders and slots.

## Features

- **Dashboard**: Real-time metrics (orders today, pending, preparing, ready, completed)
- **Order Management**: Accept, prepare, mark ready, complete orders
- **Slot Management**: View and manage pickup slots
- **Menu Management**: Update menu items and availability
- **Profile**: Vendor profile and settings

## Tech Stack

- React Native 0.73
- TypeScript
- React Navigation
- Axios for API calls
- React Native Paper for UI components

## Project Structure

```
tnt-vendor-frontend/
├── App.tsx                 # Main app component with navigation
├── src/
│   ├── context/
│   │   └── AuthContext.tsx # Authentication state management
│   ├── screens/
│   │   ├── auth/
│   │   │   └── LoginScreen.tsx
│   │   ├── home/
│   │   │   └── DashboardScreen.tsx
│   │   ├── orders/
│   │   │   └── OrdersScreen.tsx
│   │   ├── menu/
│   │   │   └── MenuScreen.tsx
│   │   └── profile/
│   │       └── ProfileScreen.tsx
│   └── services/
│       └── vendorApi.ts    # API client
└── package.json
```

## Getting Started

### Prerequisites

- Node.js >= 18
- React Native CLI
- Android Studio / Xcode

### Installation

```bash
# Install dependencies
npm install

# Run on iOS
npm run ios

# Run on Android
npm run android
```

## API Integration

The app connects to the TNT backend at `http://localhost:8000` by default.

### Available Endpoints

- `GET /v1/vendors/orders` - Get all vendor orders
- `GET /v1/vendors/orders/current-slot` - Get current slot orders
- `GET /v1/vendors/orders/upcoming` - Get upcoming orders
- `PUT /v1/vendors/orders/{id}/accept` - Accept order
- `PUT /v1/vendors/orders/{id}/prepare` - Start preparing
- `PUT /v1/vendors/orders/{id}/ready` - Mark as ready
- `PUT /v1/vendors/orders/{id}/complete` - Complete order

## Order Status Flow

```
PLACED → CONFIRMED → PREPARING → READY → PICKED
```

## Environment Variables

Create a `.env` file in the root directory:

```env
API_BASE_URL=http://localhost:8000
```

## License

MIT