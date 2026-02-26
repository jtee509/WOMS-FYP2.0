import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import PageHeader from '../components/common/PageHeader';

export default function ReferencePage() {
  return (
    <Box>
      <PageHeader
        title="Reference Data"
        description="Manage platforms, sellers, and item master data"
      />
      <Alert severity="info">
        Reference data management will be implemented here. Upload platforms,
        sellers, and item master files to populate the database.
      </Alert>
    </Box>
  );
}
