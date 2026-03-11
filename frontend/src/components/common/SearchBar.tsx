import { Search, X } from "lucide-react";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export default function SearchBar({
  value,
  onChange,
  placeholder = "Search…",
  className = "",
}: SearchBarProps) {
  return (
    <div className={`relative ${className}`}>
      <Search
        size={16}
        strokeWidth={2}
        className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-secondary/60 pointer-events-none"
      />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="form-input !pl-10 !py-1.5 w-full text-sm"
      />
      {value && (
        <button
          onClick={() => onChange("")}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary cursor-pointer"
        >
          <X size={13} />
        </button>
      )}
    </div>
  );
}
