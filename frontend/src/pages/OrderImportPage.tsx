import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import PageHeader from '../components/common/PageHeader';

export default function OrderImportPage() {
  return (
    <Box>
      <PageHeader
        title="Order Import"
        description="Upload Shopee, Lazada, or TikTok order files (CSV / Excel)"
      />
      <Alert severity="info">
        Order import form will be implemented here. Supports file upload with
        platform selection (shopee / lazada / tiktok) and seller ID.
      </Alert>
    </Box>
  );
}
