interface Props {
	title?: string;
	description: string;
}

/** OSS builds hide the runtime-limit notice; enterprise can restore the banner if needed. */
export default function RuntimeLimitBanner(_props: Props) {
	return null;
}
