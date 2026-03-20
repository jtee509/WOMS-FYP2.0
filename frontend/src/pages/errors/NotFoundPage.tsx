import { useNavigate } from 'react-router-dom';

export default function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <h1 className="text-[6rem] font-bold text-text-secondary mb-2">404</h1>
      <h2 className="text-xl font-semibold text-text-primary mb-2">
        Page Not Found
      </h2>
      <p className="text-base text-text-secondary mb-6">
        The page you are looking for does not exist.
      </p>
      <button
        type="button"
        onClick={() => navigate('/')}
        className="px-5 py-2 bg-primary hover:bg-primary-dark text-white font-semibold rounded-default hover:shadow-button-hover transition-all cursor-pointer"
      >
        Back to Dashboard
      </button>
    </div>
  );
}
