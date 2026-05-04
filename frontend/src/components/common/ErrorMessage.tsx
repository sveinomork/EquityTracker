interface Props {
  message?: string;
}

export default function ErrorMessage({ message = "Noe gikk galt." }: Props) {
  return (
    <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
      ⚠️ {message}
    </div>
  );
}
