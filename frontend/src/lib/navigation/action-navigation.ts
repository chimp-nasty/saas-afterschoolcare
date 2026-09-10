import {
	accountTabs,
	childTabs,
	type AccountTab,
	type ChildTab
} from './tabs';

type ActionNavigation = {
	childId: string | null;
	target: AccountTab | ChildTab;
};

function isAccountTab(value: string): value is AccountTab {
	return Object.values(accountTabs).includes(value as AccountTab);
}

function isChildTab(value: string): value is ChildTab {
	return Object.values(childTabs).includes(value as ChildTab);
}

export function buildActionHref(
	locationCode: string,
	action: {
		childId: string | null;
		target: string;
	}
): string | null {
	if (action.childId) {
		if (!isChildTab(action.target)) {
			return null;
		}

		return `/${locationCode}/account/children/${action.childId}?state=${action.target}`;
	}

	if (!isAccountTab(action.target)) {
		return null;
	}

	return `/${locationCode}/account?state=${action.target}`;
}