import type { PickupRelation, PickupResponse } from '$lib/api/schema';

// People a family can add besides the account holder (enforced by the
// database too).
export const PICKUP_LIMIT = 3;

export const PICKUP_RELATION_LABELS: Record<PickupRelation, string> = {
    account_holder: 'Account holder',
    grandparent: 'Grandparent',
    aunt_uncle: 'Aunt or uncle',
    family_friend: 'Family friend',
    neighbour: 'Neighbour',
    nanny_babysitter: 'Nanny or babysitter',
    other: 'Other'
};

// "Other" shows what the family typed instead.
export function relationLabel(
    pickup: Pick<PickupResponse, 'relation' | 'relation_other'>
): string {
    return pickup.relation === 'other' && pickup.relation_other
        ? pickup.relation_other
        : PICKUP_RELATION_LABELS[pickup.relation];
}
