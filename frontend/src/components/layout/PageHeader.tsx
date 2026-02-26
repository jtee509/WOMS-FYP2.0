interface PageHeaderProps {
  title: string;
  description?: string;
}

export default function PageHeader({ title, description }: PageHeaderProps) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-semibold text-text-primary mb-1">{title}</h1>
      {description && (
        <p className="text-base text-text-secondary">{description}</p>
      )}
    </div>
  );
}
