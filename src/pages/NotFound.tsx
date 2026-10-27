import { Link } from "react-router-dom";

import { PageHeader } from "@/components/PageHeader";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

export function NotFoundPage() {
  useDocumentTitle("Page not found");
  return (
    <>
      <PageHeader title="Page not found">There is nothing at this address.</PageHeader>
      <Link to="/" className="btn">
        Back to the overview
      </Link>
    </>
  );
}
