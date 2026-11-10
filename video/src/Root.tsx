import React from 'react';
import {Composition} from 'remotion';
import {Film, FILM_LEN} from './Film';
import {Opening, OPENING_LEN} from './Opening';

export const Root: React.FC = () => (
  <>
    <Composition id="AgentAudit" component={Film} durationInFrames={FILM_LEN} fps={30} width={1920} height={1080} />
    <Composition id="Opening" component={Opening} durationInFrames={OPENING_LEN} fps={30} width={1920} height={1080} />
  </>
);
