import PageHeader from '../components/layout/PageHeader';

export default function OrderImportPage() {
  return (
    <div>
      <PageHeader
        title="Order Import"
        description="Upload Shopee, Lazada, or TikTok order files (CSV / Excel)"
      />
      <div className="bg-info-bg text-info-text rounded-default px-4 py-3 text-sm">
        Order import form will be implemented here. Supports file upload with
        platform selection (shopee / lazada / tiktok) and seller ID.
      </div>
    </div>
  );
}
