import { Placeholder } from "@/components/placeholder";
import { ApiStatus } from "@/components/api-status";
export default function Page() {
  return (
    <>
      <Placeholder
        title="Observability demo"
        description="Understand the health and behavior of the system you’re building."
      />
      <div className="mt-6">
        <ApiStatus />
      </div>
    </>
  );
}
