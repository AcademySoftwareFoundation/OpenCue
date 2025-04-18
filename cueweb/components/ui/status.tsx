type StatusProps = {
  status: string;
};

// prettier-ignore
const STATUS_COLORS = {
  SUCCEEDED: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  FINISHED: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  RUNNING: "bg-yellow-100 text-yellow-800 dark:bg-yellow-700 dark:text-yellow-300",
  WAITING: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  PAUSED: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  DEPEND: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
  DEPENDENCY: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
  DEAD: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  FAILING: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  DEFAULT: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
};

export function Status({ status }: StatusProps) {
  const colors = STATUS_COLORS[status.toUpperCase() as keyof typeof STATUS_COLORS] || STATUS_COLORS.DEFAULT;

  return (
    <span className={`flex flex-row justify-center text-xs mr-2 px-1.5 py-0.5 rounded hover:cursor-pointer ${colors}`}>
      {status}
    </span>
  );
}
