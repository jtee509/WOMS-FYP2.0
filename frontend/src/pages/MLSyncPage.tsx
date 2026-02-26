import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import PageHeader from '../components/common/PageHeader';

export default function MLSyncPage() {
  return (
    <Box>
      <PageHeader
        title="ML Staging"
        description="Sync order data to the ML staging database"
      />
      <Alert severity="info">
        ML sync controls will be implemented here. Initialise the ML schema
        and sync staged orders from woms_db to ml_woms_db.
      </Alert>
    </Box>
  );
}
