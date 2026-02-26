import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1565C0',
      light: '#1E88E5',
      dark: '#0D47A1',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#FF8F00',
      light: '#FFA726',
      dark: '#E65100',
      contrastText: '#FFFFFF',
    },
    background: {
      default: '#F5F7FA',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#1A1A2E',
      secondary: '#555770',
    },
    error: {
      main: '#D32F2F',
    },
    warning: {
      main: '#ED6C02',
    },
    success: {
      main: '#2E7D32',
    },
    info: {
      main: '#0288D1',
    },
    divider: '#E0E0E0',
  },
  typography: {
    fontFamily: '"Montserrat", "Helvetica", "Arial", sans-serif',
    h1: { fontWeight: 700 },
    h2: { fontWeight: 700 },
    h3: { fontWeight: 600 },
    h4: { fontWeight: 600 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
    subtitle1: { fontWeight: 500 },
    subtitle2: { fontWeight: 500 },
    button: { fontWeight: 600, textTransform: 'none' },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '8px 20px',
          fontSize: '0.875rem',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          },
        },
        containedPrimary: {
          backgroundColor: '#1565C0',
          '&:hover': {
            backgroundColor: '#0D47A1',
          },
        },
        containedSecondary: {
          backgroundColor: '#FF8F00',
          '&:hover': {
            backgroundColor: '#E65100',
          },
        },
        outlinedPrimary: {
          borderColor: '#1565C0',
          color: '#1565C0',
          '&:hover': {
            backgroundColor: 'rgba(21,101,192,0.08)',
            borderColor: '#0D47A1',
          },
        },
        outlinedSecondary: {
          borderColor: '#FF8F00',
          color: '#FF8F00',
          '&:hover': {
            backgroundColor: 'rgba(255,143,0,0.08)',
            borderColor: '#E65100',
          },
        },
      },
    },
    MuiCheckbox: {
      styleOverrides: {
        root: {
          color: '#90A4AE',
          '&.Mui-checked': {
            color: '#1565C0',
          },
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        standardSuccess: {
          backgroundColor: '#E8F5E9',
          color: '#1B5E20',
        },
        standardError: {
          backgroundColor: '#FFEBEE',
          color: '#B71C1C',
        },
        standardWarning: {
          backgroundColor: '#FFF3E0',
          color: '#E65100',
        },
        standardInfo: {
          backgroundColor: '#E1F5FE',
          color: '#01579B',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)',
          borderRadius: 12,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        },
      },
    },
  },
});

export default theme;
