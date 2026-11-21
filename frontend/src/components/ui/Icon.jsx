import React from 'react';
import {
  Ban, Building2, Calculator, Calendar, File, FileText, Flame, Hourglass, Landmark, Milk, Package,
  Shield, Star, TrendingUp, Truck, Users, Wallet, Wrench,
} from 'lucide-react';

// Data files refer to icons by name; this maps the name to a Lucide icon.
const ICONS = {
  ban: Ban, building: Building2, calculator: Calculator, calendar: Calendar, file: File, fileText: FileText,
  flame: Flame, hourglass: Hourglass, landmark: Landmark, milk: Milk, package: Package, shield: Shield,
  star: Star, trendingUp: TrendingUp, truck: Truck, users: Users, wallet: Wallet, wrench: Wrench,
};

export default function Icon({ name, ...props }) {
  const Cmp = ICONS[name] || File;
  return <Cmp strokeWidth={1.8} {...props} />;
}
