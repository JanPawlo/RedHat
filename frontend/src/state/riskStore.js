import { getRiskPage } from '../api/pagesApi.js';
import { risk as mockRisk } from '../data/mockData.js';
import { usePageData } from './pageDataStore.js';

/** Risk page data computed by fixed rules on the database; the mock until it arrives. */
export function useRisk() {
  return usePageData('risk', getRiskPage, mockRisk);
}
