import React from 'react';
import { Link } from "react-router-dom";

import { useAuth } from '../../hooks/useAuth';
import { getCSRFToken } from "../../utils/csrf";


export function EndpointList() {
    return (
        <div>
            <span>foo!</span>
        </div>
    )
}