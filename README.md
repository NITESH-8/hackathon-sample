# 🚀 Log Analysis System - React Frontend

A **stunning, modern React.js frontend** for the AI-powered Log Analysis System with intelligent log processing, similarity detection, and team collaboration features.

![React](https://img.shields.io/badge/React-18.2.0-blue?style=for-the-badge&logo=react)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3.0-purple?style=for-the-badge&logo=bootstrap)
![TypeScript](https://img.shields.io/badge/JavaScript-ES6+-yellow?style=for-the-badge&logo=javascript)

## ✨ Design Features

### 🎨 **Modern Glassmorphism UI**
- **Glassmorphism effects** with backdrop blur and transparency
- **Gradient backgrounds** and smooth animations
- **Custom typography** with Inter and Fira Code fonts
- **Responsive design** that works on all devices

### 🌈 **Beautiful Color Scheme**
- **Primary Gradient**: `#667eea` → `#764ba2`
- **Accent Colors**: Success, Warning, Danger with gradients
- **Glass Effects**: Semi-transparent backgrounds with blur
- **Smooth Transitions**: Cubic-bezier animations throughout

### 🎯 **Enhanced User Experience**
- **Drag & Drop Upload** with visual feedback
- **Animated Loading States** with custom spinners
- **Toast Notifications** for user feedback
- **Hover Effects** and micro-interactions
- **Professional Typography** with proper hierarchy

## 🚀 Core Features

- 🔐 **Authentication** - Secure login/signup with JWT tokens
- 📁 **File Upload** - Drag & drop log file upload with validation
- 🧠 **AI Analysis** - GenAPI-powered log analysis and insights
- 🔍 **Similarity Detection** - Automatic comparison with previous logs (≥80% similarity)
- 📊 **Log History** - Comprehensive log management with filtering
- 👥 **Team Collaboration** - Multi-user support with visibility controls
- 📱 **Responsive Design** - Modern UI with Bootstrap 5
- ⚡ **Real-time Processing** - Live upload progress and status updates

## 🎨 Design System

### **Typography**
- **Primary Font**: Inter (300-800 weights)
- **Code Font**: Fira Code (monospace)
- **Hierarchy**: Clear heading structure with proper spacing

### **Color Palette**
```css
Primary: #667eea → #764ba2 (Gradient)
Success: #4caf50 → #45a049
Warning: #ffa726 → #ff9800
Danger: #ff6b6b → #ee5a52
Info: #2196f3 → #1976d2
```

### **Components**
- **Cards**: Glassmorphism with subtle shadows
- **Buttons**: Gradient backgrounds with hover effects
- **Forms**: Rounded inputs with focus states
- **Modals**: Full-screen with gradient headers
- **Tables**: Clean design with hover states

## Tech Stack

- **React 18** - Modern React with hooks
- **React Router** - Client-side routing
- **Axios** - HTTP client for API communication
- **Bootstrap 5** - Responsive UI framework
- **React Bootstrap** - Bootstrap components for React
- **React Dropzone** - File upload with drag & drop
- **React Toastify** - Toast notifications
- **Font Awesome** - Icons

## Prerequisites

- Node.js 16+ and npm
- Python backend running on http://localhost:5000
- Elasticsearch running on http://localhost:9200

## 🚀 Quick Start

### **Prerequisites**
- Node.js 16+ and npm
- Python backend running on http://localhost:5000
- Elasticsearch running on http://localhost:9200

### **Installation**

1. **Clone and install dependencies:**
   ```bash
   git clone <repository-url>
   cd log-analysis-frontend
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm start
   ```

3. **Open your browser:**
   Navigate to **http://localhost:3000** 🎉

### **Production Build**
```bash
npm run build
```

### **Development Workflow**
```bash
# Start backend (Python Flask)
python app.py

# Start Elasticsearch
docker start elasticsearch

# Start React frontend
npm start
```

## Available Scripts

- `npm start` - Start development server
- `npm build` - Build for production
- `npm test` - Run tests
- `npm eject` - Eject from Create React App

## Project Structure

```
src/
├── components/          # React components
│   ├── Login.js        # Login form
│   ├── Signup.js       # Registration form
│   ├── Dashboard.js    # Main dashboard
│   ├── Navbar.js       # Navigation bar
│   ├── UploadArea.js   # File upload component
│   ├── RecordsList.js  # Records display
│   ├── LogHistory.js   # Log history modal
│   ├── RecordModal.js  # Record details modal
│   ├── AnalysisModal.js # Analysis results modal
│   └── QuestionModal.js # Q&A modal
├── services/           # API services
│   ├── ApiService.js   # Main API client
│   └── AuthService.js  # Authentication service
├── App.js             # Main app component
├── App.css            # App styles
├── index.js           # Entry point
└── index.css          # Global styles
```

## API Integration

The frontend communicates with the Python backend through RESTful APIs:

- **Authentication**: `/auth/login`, `/auth/signup`
- **Profile**: `/profile/me`
- **Records**: `/records`, `/records/{id}`
- **Upload**: `/upload`
- **Analysis**: `/genapi/analyze`
- **Similarity**: `/records/{id}/similar`
- **Download**: `/download`

## Key Features

### 🔐 Authentication
- Secure JWT-based authentication
- User profile management
- Team-based access control

### 📁 File Upload
- Drag & drop interface
- File type validation (.log, .txt, .out, .err)
- Size limit (50MB)
- Context input for additional information

### 🧠 AI Analysis
- GenAPI integration for intelligent analysis
- Problem detection with severity scoring
- Root cause analysis
- Recommendations and insights

### 🔍 Similarity Detection
- Automatic vector embedding comparison
- Shows all matches ≥80% similarity
- Clickable links to similar records
- Show more/less functionality

### 📊 Log History
- Comprehensive log management table
- Tag-based filtering
- Owner information display
- Raw log download functionality
- Similarity percentage display

### 📱 Responsive Design
- Mobile-friendly interface
- Bootstrap 5 components
- Modern UI with smooth animations
- Toast notifications for user feedback

## Environment Variables

Create a `.env` file in the root directory:

```env
REACT_APP_API_BASE_URL=http://localhost:5000
REACT_APP_ELASTICSEARCH_URL=http://localhost:9200
```

## Development

1. **Start the backend server** (Python Flask):
   ```bash
   python app.py
   ```

2. **Start Elasticsearch**:
   ```bash
   docker start elasticsearch
   ```

3. **Start the React development server**:
   ```bash
   npm start
   ```

4. **Open http://localhost:3000** in your browser

## Production Build

```bash
npm run build
```

This creates a `build` folder with optimized production files.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is part of the Log Analysis System. See the main project for licensing information.

## Support

For issues and questions, please refer to the main project documentation or create an issue in the repository.