import React from 'react';
import { Link } from 'react-router-dom';
import { Compass } from 'lucide-react';
import { Button, IconCircle, PageHeader } from '../components/ui/primitives.jsx';

export default function ComingSoon({ icon = Compass, title, text }) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={title} />
      <div className="card flex flex-col items-center gap-4 py-20 text-center">
        <IconCircle icon={icon} size={72} />
        <p className="t-title">Coming soon</p>
        <p className="max-w-md t-body text-text-muted">{text}</p>
        <Link to="/">
          <Button kind="soft">Back to dashboard</Button>
        </Link>
      </div>
    </div>
  );
}
