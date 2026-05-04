interface Props {
  message?: string;
}

export default function EmptyState({ message = "Ingen data." }: Props) {
  return (
    <div className="text-center py-12 text-gray-400 text-sm">
      <p className="text-3xl mb-2">📭</p>
      <p>{message}</p>
    </div>
  );
}
